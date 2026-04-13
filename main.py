from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import hashlib
import json
import asyncio
from datetime import datetime

# Import your existing modules
from neo4j import GraphDatabase
from google.generativeai import GenerativeModel, configure
from langchain_neo4j import Neo4jGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from PIL import Image
import io
import os

# Configuration
# ⚠️ YOUR API KEY
GOOGLE_API_KEY = "AIzaSyA-mPnNNnhhjTv5SOT4DG_7_We4q9OWqtA"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Configure with gemini-2.5-flash (universally available)
configure(api_key=GOOGLE_API_KEY)
flash_model = GenerativeModel("gemini-2.5-flash")  # ✅ Changed to gemini-2.5-flash
vision_model = GenerativeModel("gemini-2.5-flash")  # ✅ For images

NEO4J_URI = "neo4j+s://d2a5b462.databases.neo4j.io"
NEO4J_USERNAME = "d2a5b462"
NEO4J_PASSWORD = "E42fjl-1P6qr5-93ti0ckFCNDLQVvPZhbixzpl3CN7A"

# Helper function for Gemini API
def generate_content(prompt, image=None):
    """Generate content using Gemini API"""
    try:
        if image:
            # Use vision model for images
            response = vision_model.generate_content([prompt, image], stream=False)
        else:
            # Use text model for text only
            response = flash_model.generate_content(prompt, stream=False)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        raise

# Initialize FastAPI app
app = FastAPI(title="MediGraph Healthcare API", version="1.0.0")

# CORS Configuration - Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class LoginRequest(BaseModel):
    user_id: str
    password: str

class RegisterRequest(BaseModel):
    user_id: str
    password: str
    user_type: str  # "Patient" or "Doctor"

class LoginResponse(BaseModel):
    message: str
    user_type: str

# Helper Functions
def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_neo4j_driver():
    """Get Neo4j database driver"""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def check_user_exists(user_id: str):
    """Check if user exists in database"""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (u:User {id: $id}) RETURN u",
                id=user_id
            )
            exists = result.single() is not None
        return exists
    finally:
        driver.close()

def check_patient_exists(patient_id: str):
    """Check if patient exists in database"""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (p:Patient {id: $id}) RETURN p",
                id=patient_id
            )
            exists = result.single() is not None
        return exists
    finally:
        driver.close()

# Authentication Endpoints
@app.post("/api/auth/register")
async def register_user(request: RegisterRequest):
    """Register a new user (Patient or Doctor)"""
    try:
        # Validate user type
        if request.user_type not in ["Patient", "Doctor"]:
            raise HTTPException(status_code=400, detail="Invalid user type")
        
        # Check if user already exists
        if check_user_exists(request.user_id):
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create user in Neo4j
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                session.run(
                    "CREATE (u:User {id: $id, password: $password, type: $type})",
                    id=request.user_id,
                    password=hash_password(request.password),
                    type=request.user_type
                )
            return {"message": "Registration successful", "user_type": request.user_type}
        finally:
            driver.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/auth/login", response_model=LoginResponse)
async def login_user(request: LoginRequest):
    """Authenticate user and return user type"""
    try:
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                result = session.run(
                    "MATCH (u:User {id: $id}) RETURN u.password as pwd, u.type as type",
                    id=request.user_id
                )
                record = result.single()
                
                if not record:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                
                if record["pwd"] != hash_password(request.password):
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                
                return LoginResponse(
                    message="Login successful",
                    user_type=record["type"]
                )
        finally:
            driver.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

# Agent Processing Functions
def agent_ocr(image_bytes):
    """Agent 1: OCR Text Extraction"""
    image = Image.open(io.BytesIO(image_bytes))
    return generate_content("Extract all text from this image.", image)

def agent_correction(extracted_text):
    """Agent 2: Text Correction"""
    prompt = f"Correct only the spelling mistakes in the following text. Do not add, remove, or change anything else:\n\n{extracted_text}"
    return generate_content(prompt)

def agent_understanding(corrected_text):
    """Agent 3: Text Understanding"""
    prompt = f"Extract only the medically relevant information from the following text. Format as a structured list:\n\n{corrected_text}"
    return generate_content(prompt)

def agent_fhir_format(understood_text):
    """Agent 4: FHIR Format Conversion"""
    prompt = f"""Convert the following medical report into FHIR JSON format.
Only include medically relevant data such as diagnosis, medications, allergies, observations.

Text:
{understood_text}
"""
    fhir_json = generate_content(prompt)
    
    # Clean up markdown
    if fhir_json.startswith("```"):
        lines = fhir_json.split("\n")
        fhir_json = "\n".join(line for line in lines if not line.startswith("```"))
    
    return fhir_json.strip()

def agent_graph_db(understood_text, patient_id):
    """Agent 5: Graph Database Creation"""
    patient_exists = check_patient_exists(patient_id)
    
    if patient_exists:
        prompt = f"""Generate Neo4j Cypher queries to ADD new medical data to EXISTING Patient with id '{patient_id}'.
DO NOT recreate the Patient node.
Only CREATE new nodes (Medication, Diagnosis, Observation) and connect to existing Patient.
Use double quotes for strings.
Output only raw Cypher queries.

Text:
{understood_text}
"""
    else:
        prompt = f"""Generate Neo4j Cypher queries to CREATE a new Patient node with id '{patient_id}' and related medical data.
Use double quotes for strings.
Output only raw Cypher queries.

Text:
{understood_text}
"""
    
    raw_cypher = generate_content(prompt)
    
    if raw_cypher.startswith("```"):
        raw_cypher = "\n".join(line for line in raw_cypher.splitlines() if not line.startswith("```"))
    
    # Execute Cypher queries
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            for query in raw_cypher.split(";"):
                query = query.strip()
                if query:
                    try:
                        session.run(query)
                    except Exception as query_error:
                        print(f"Skipped query: {str(query_error)[:100]}")
                        continue
    finally:
        driver.close()
    
    return raw_cypher

def agent_final_output(patient_id):
    """Agent 6: Final Response Generation"""
    try:
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                result = session.run(
                    "MATCH (p:Patient {id: $id})-[r]-(n) RETURN p, type(r) as relationship, n, labels(n) as labels, properties(n) as props",
                    id=patient_id
                )
                patient_data = [record.data() for record in result]
        finally:
            driver.close()
        
        if not patient_data:
            return "No patient data found in database."
        
        formatted_data = json.dumps(patient_data, indent=2)
        
        prompt = f"""Based on this patient data, provide:
1. Brief summary of condition
2. Prescription recommendations
3. Further action recommendations

Patient Data:
{formatted_data}
"""
        
        # Use ChatGoogleGenerativeAI with gemini-2.5-flash
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0.3)
        result = llm.invoke(prompt)
        
        if hasattr(result, 'content'):
            return result.content
        else:
            return str(result)
            
    except Exception as e:
        return f"Error: {str(e)}"

# Prescription Processing Endpoint
@app.post("/api/process-prescription")
async def process_prescription(
    file: UploadFile = File(...),
    patient_id: str = Form(...)
):
    """Process prescription image through 6-agent pipeline"""
    
    async def event_generator():
        try:
            image_bytes = await file.read()
            
            # Agent 1: OCR
            yield f"data: {json.dumps({'agent': 1, 'status': 'processing'})}\n\n"
            await asyncio.sleep(0.5)
            extracted_text = agent_ocr(image_bytes)
            yield f"data: {json.dumps({'agent': 1, 'result': extracted_text[:200] + '...'})}\n\n"
            
            # Agent 2: Correction
            yield f"data: {json.dumps({'agent': 2, 'status': 'processing'})}\n\n"
            await asyncio.sleep(0.5)
            corrected_text = agent_correction(extracted_text)
            yield f"data: {json.dumps({'agent': 2, 'result': corrected_text[:200] + '...'})}\n\n"
            
            # Agent 3: Understanding
            yield f"data: {json.dumps({'agent': 3, 'status': 'processing'})}\n\n"
            await asyncio.sleep(0.5)
            understood_text = agent_understanding(corrected_text)
            yield f"data: {json.dumps({'agent': 3, 'result': understood_text[:200] + '...'})}\n\n"
            
            # Agent 4: FHIR Format
            yield f"data: {json.dumps({'agent': 4, 'status': 'processing'})}\n\n"
            await asyncio.sleep(0.5)
            fhir_json = agent_fhir_format(understood_text)
            yield f"data: {json.dumps({'agent': 4, 'result': 'FHIR format created'})}\n\n"
            
            # Agent 5: Graph DB
            yield f"data: {json.dumps({'agent': 5, 'status': 'processing'})}\n\n"
            await asyncio.sleep(0.5)
            graph_queries = agent_graph_db(understood_text, patient_id)
            yield f"data: {json.dumps({'agent': 5, 'result': 'Data stored in graph database'})}\n\n"
            
            # Agent 6: Final Analysis
            yield f"data: {json.dumps({'agent': 6, 'status': 'processing'})}\n\n"
            await asyncio.sleep(0.5)
            final_output = agent_final_output(patient_id)
            yield f"data: {json.dumps({'agent': 6, 'result': 'Analysis complete'})}\n\n"
            
            # Send final result
            yield f"data: {json.dumps({'final': final_output})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )

# Patient Summary Endpoint
@app.get("/api/patient/{patient_id}/summary")
async def get_patient_summary(patient_id: str):
    """Get patient medical summary"""
    try:
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                result = session.run(
                    "MATCH (p:Patient {id: $id})-[r]-(n) RETURN p, type(r) as rel, n, labels(n) as labels, properties(n) as props",
                    id=patient_id
                )
                data = [record.data() for record in result]
        finally:
            driver.close()
        
        if not data:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Extract data
        medications = []
        diagnoses = []
        
        for record in data:
            labels = record.get('labels', [])
            props = record.get('props', {})
            
            if 'Medication' in labels:
                med = props.get('name', 'Unknown')
                if 'dosage' in props:
                    med += f" - {props['dosage']}"
                medications.append(med)
            elif 'Diagnosis' in labels:
                diagnoses.append(props.get('condition', props.get('name', 'Unknown')))
        
        # Generate summary
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0.3)
        
        prompt = f"""Analyze and provide summary, medications, diagnoses, and recommendations.

Patient Data: {json.dumps(data, indent=2)}"""
        
        result = llm.invoke(prompt)
        summary_text = result.content if hasattr(result, 'content') else str(result)
        
        return {
            "summary": summary_text,
            "medications": medications if medications else ["No medications recorded"],
            "diagnoses": diagnoses if diagnoses else ["No diagnoses recorded"],
            "recommendations": summary_text
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Health Check
@app.get("/")
async def root():
    return {
        "message": "MediGraph Healthcare API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)