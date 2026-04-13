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
GOOGLE_API_KEY = "AIzaSyA5nm956oRec8eSAKMjm6kGK0wfe57oxs8"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

configure(api_key=GOOGLE_API_KEY)
flash_model = GenerativeModel("gemini-2.5-flash")
vision_model = GenerativeModel("gemini-2.5-flash")

NEO4J_URI = "neo4j+s://d2a5b462.databases.neo4j.io"
NEO4J_USERNAME = "d2a5b462"
NEO4J_PASSWORD = "E42fjl-1P6qr5-93ti0ckFCNDLQVvPZhbixzpl3CN7A"

def neo4j_json_serializer(obj):
    """Handle Neo4j-specific types that aren't JSON serializable by default."""
    # Neo4j temporal types all expose __str__ in ISO format
    type_name = type(obj).__name__
    if type_name in ("DateTime", "Date", "Time", "Duration", "Point"):
        return str(obj)
    # Fallback for anything else unexpected
    return str(obj)

def safe_json_dumps(data, **kwargs):
    """json.dumps with Neo4j type support."""
    return json.dumps(data, default=neo4j_json_serializer, **kwargs)

def generate_content(prompt, image=None):
    """Generate content using Gemini API"""
    try:
        if image:
            response = vision_model.generate_content([prompt, image], stream=False)
        else:
            response = flash_model.generate_content(prompt, stream=False)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        raise

app = FastAPI(title="MediGraph Healthcare API", version="1.0.0")

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

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def check_user_exists(user_id: str):
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (u:User {id: $id}) RETURN u",
                id=user_id
            )
            return result.single() is not None
    finally:
        driver.close()

def check_patient_exists(aadhaar: str):
    """Check if patient exists using Aadhaar number"""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (p:Patient {aadhaar: $aadhaar}) RETURN p",
                aadhaar=aadhaar
            )
            return result.single() is not None
    finally:
        driver.close()

def ensure_patient_node(aadhaar: str):
    """
    Guarantee the Patient node exists with aadhaar property BEFORE
    running the AI-generated Cypher. This fixes the 'No patient data found' bug.
    """
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            session.run(
                """
                MERGE (p:Patient {aadhaar: $aadhaar})
                ON CREATE SET p.created_at = datetime()
                ON MATCH SET p.updated_at = datetime()
                """,
                aadhaar=aadhaar
            )
    finally:
        driver.close()

# Authentication Endpoints
@app.post("/api/auth/register")
async def register_user(request: RegisterRequest):
    """Register a new user (Patient or Doctor)"""
    try:
        if request.user_type not in ["Patient", "Doctor"]:
            raise HTTPException(status_code=400, detail="Invalid user type")

        if check_user_exists(request.user_id):
            raise HTTPException(status_code=400, detail="User already exists")

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
    """Agent 3: Text Understanding — strips personal info, keeps medical data only"""
    prompt = f"""Extract ONLY the medically relevant information from the following text.
DO NOT include any personal identifiable information such as patient name, address, phone number, or email.
Format as a structured list of medical facts only (diagnosis, medications, dosage, observations, allergies, lab results, etc.).

Text:
{corrected_text}
"""
    return generate_content(prompt)

def agent_fhir_format(understood_text):
    """Agent 4: FHIR Format Conversion"""
    prompt = f"""Convert the following medical report into FHIR JSON format.
Only include medically relevant data such as diagnosis, medications, allergies, observations.
Do NOT include patient name or personal details — use only aadhaar as the patient identifier.

Text:
{understood_text}
"""
    fhir_json = generate_content(prompt)

    if fhir_json.startswith("```"):
        lines = fhir_json.split("\n")
        fhir_json = "\n".join(line for line in lines if not line.startswith("```"))

    return fhir_json.strip()

def agent_graph_db(understood_text, aadhaar: str):
    """Agent 5: Graph Database — links data to Patient node via Aadhaar"""

    patient_exists = check_patient_exists(aadhaar)

    # Always ensure the Patient node exists first (fixes 'No patient data found' bug)
    ensure_patient_node(aadhaar)

    if patient_exists:
        prompt = f"""Generate Neo4j Cypher queries to ADD new medical data to an EXISTING Patient node.
The Patient node has the property: aadhaar = "{aadhaar}"
DO NOT recreate the Patient node. Use MATCH to find it.
Only CREATE new nodes (Medication, Diagnosis, Observation, Allergy, LabResult) and MERGE relationships to the existing Patient.
Use double quotes for all string values.
Do NOT store patient name, address, phone, or any personal info — only medical data.
Output ONLY raw Cypher queries separated by semicolons. No explanations, no markdown.

Medical Data:
{understood_text}
"""
    else:
        prompt = f"""Generate Neo4j Cypher queries to link medical data to an existing Patient node.
The Patient node has the property: aadhaar = "{aadhaar}"
Use MATCH (p:Patient {{aadhaar: "{aadhaar}"}}) to find the patient — DO NOT create it again.
CREATE new nodes (Medication, Diagnosis, Observation, Allergy, LabResult) and MERGE relationships to the Patient.
Use double quotes for all string values.
Do NOT store patient name, address, phone, or any personal info — only medical data.
Output ONLY raw Cypher queries separated by semicolons. No explanations, no markdown.

Medical Data:
{understood_text}
"""

    raw_cypher = generate_content(prompt)

    if raw_cypher.startswith("```"):
        raw_cypher = "\n".join(
            line for line in raw_cypher.splitlines() if not line.startswith("```")
        )

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
                        print(f"Skipped query: {str(query_error)[:150]}")
                        continue
    finally:
        driver.close()

    return raw_cypher

def agent_final_output(aadhaar: str):
    """Agent 6: Final Response Generation — queries by Aadhaar"""
    try:
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (p:Patient {aadhaar: $aadhaar})
                    OPTIONAL MATCH (p)-[r]-(n)
                    RETURN p, type(r) as relationship, n, labels(n) as labels, properties(n) as props
                    """,
                    aadhaar=aadhaar
                )
                patient_data = [record.data() for record in result]
        finally:
            driver.close()

        if not patient_data or all(r.get('n') is None for r in patient_data):
            return "Patient record created but no medical data linked yet. Upload a prescription to begin."

        formatted_data = safe_json_dumps(patient_data, indent=2)

        prompt = f"""Based on this patient's medical data (identified by Aadhaar), provide:
1. Brief summary of condition
2. Current medications and dosage
3. Active diagnoses
4. Further action / follow-up recommendations

Patient Data:
{formatted_data}
"""
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3
        )
        result = llm.invoke(prompt)

        return result.content if hasattr(result, 'content') else str(result)

    except Exception as e:
        return f"Error generating summary: {str(e)}"

# Prescription Processing Endpoint
@app.post("/api/process-prescription")
async def process_prescription(
    file: UploadFile = File(...),
    patient_id: str = Form(...)   # patient_id here IS the Aadhaar number
):
    """Process prescription image through 6-agent pipeline"""

    aadhaar = patient_id  # treat patient_id as Aadhaar throughout

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
            graph_queries = agent_graph_db(understood_text, aadhaar)
            yield f"data: {json.dumps({'agent': 5, 'result': 'Data stored in graph database'})}\n\n"

            # Agent 6: Final Analysis
            yield f"data: {json.dumps({'agent': 6, 'status': 'processing'})}\n\n"
            await asyncio.sleep(0.5)
            final_output = agent_final_output(aadhaar)
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
@app.get("/api/patient/{aadhaar}/summary")
async def get_patient_summary(aadhaar: str):
    """Get patient medical summary by Aadhaar"""
    try:
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (p:Patient {aadhaar: $aadhaar})
                    OPTIONAL MATCH (p)-[r]-(n)
                    RETURN p, type(r) as rel, n, labels(n) as labels, properties(n) as props
                    """,
                    aadhaar=aadhaar
                )
                data = [record.data() for record in result]
        finally:
            driver.close()

        if not data or all(r.get('n') is None for r in data):
            raise HTTPException(status_code=404, detail="Patient not found")

        medications = []
        diagnoses = []

        for record in data:
            labels = record.get('labels', []) or []
            props = record.get('props', {}) or {}

            if 'Medication' in labels:
                med = props.get('name', 'Unknown')
                if 'dosage' in props:
                    med += f" - {props['dosage']}"
                medications.append(med)
            elif 'Diagnosis' in labels:
                diagnoses.append(props.get('condition', props.get('name', 'Unknown')))

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3
        )

        prompt = f"""Analyze and provide summary, medications, diagnoses, and recommendations.
Do not mention or infer patient name — use Aadhaar as the identifier only.

Patient Data: {safe_json_dumps(data, indent=2)}"""

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