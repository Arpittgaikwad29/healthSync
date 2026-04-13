from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, TypedDict, Annotated
import hashlib
import json
import asyncio
from datetime import datetime
import operator

# ── Core imports ──────────────────────────────────────────────────────────────
from neo4j import GraphDatabase
from google.generativeai import GenerativeModel, configure
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from PIL import Image
import io
import os

# ── LangGraph ─────────────────────────────────────────────────────────────────
from langgraph.graph import StateGraph, END

# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════
GOOGLE_API_KEY = "AIzaSyCY2MF4yyYvdHH75cmyQNDnipErGoNAUwo"
GROQ_API_KEY   = "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"

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
os.environ["GROQ_API_KEY"]   = GROQ_API_KEY

configure(api_key=GOOGLE_API_KEY)

# Agent 1 stays on Gemini (vision / OCR)
vision_model = GenerativeModel("gemini-2.5-flash")

# Agents 2-6 use Groq – llama-3.3-70b-versatile is fast and accurate
groq_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0.2,
)

NEO4J_URI      = "neo4j+s://d14449d0.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "jbEKrt_HeJRWunPmZbBHMJP-HVlHiybXxTV-mpIrP7A"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════
def neo4j_json_serializer(obj):
    type_name = type(obj).__name__
    if type_name in ("DateTime", "Date", "Time", "Duration", "Point"):
        return str(obj)
    return str(obj)


def safe_json_dumps(data, **kwargs):
    return json.dumps(data, default=neo4j_json_serializer, **kwargs)


def strip_markdown(text: str) -> str:
    import re
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'#{1,6}\s?', '', text)
    text = re.sub(r'`{1,3}', '', text)
    text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


def check_patient_exists(aadhaar: str) -> bool:
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (p:Patient {aadhaar: $aadhaar}) RETURN p",
                aadhaar=aadhaar,
            )
            return result.single() is not None
    finally:
        driver.close()


def ensure_patient_node(aadhaar: str):
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            session.run(
                """
                MERGE (p:Patient {aadhaar: $aadhaar})
                ON CREATE SET p.created_at = datetime()
                ON MATCH  SET p.updated_at = datetime()
                """,
                aadhaar=aadhaar,
            )
    finally:
        driver.close()


def check_user_exists(user_id: str) -> bool:
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (u:User {id: $id}) RETURN u",
                id=user_id,
            )
            return result.single() is not None
    finally:
        driver.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# LangGraph State
# ══════════════════════════════════════════════════════════════════════════════
class PrescriptionState(TypedDict):
    # inputs
    image_bytes: bytes
    aadhaar: str
    # pipeline outputs (each agent writes its own key)
    extracted_text: str
    corrected_text: str
    understood_text: str
    fhir_json: str
    graph_queries: str
    final_output: str
    # streaming progress (list so reducer can append)
    events: Annotated[list, operator.add]
    error: str


# ══════════════════════════════════════════════════════════════════════════════
# Agent Node Functions
# ══════════════════════════════════════════════════════════════════════════════

# ── Agent 1: OCR (Gemini Vision) ──────────────────────────────────────────────
def node_ocr(state: PrescriptionState) -> dict:
    try:
        image = Image.open(io.BytesIO(state["image_bytes"]))
        response = vision_model.generate_content(
            ["Extract all text from this image.", image], stream=False
        )
        text = response.text.strip()
        return {
            "extracted_text": text,
            "events": [{"agent": 1, "result": text[:200] + "..."}],
        }
    except Exception as e:
        return {"error": f"OCR failed: {e}", "events": [{"agent": 1, "error": str(e)}]}


# ── Agent 2: Correction (Groq) ────────────────────────────────────────────────
def node_correction(state: PrescriptionState) -> dict:
    if state.get("error"):
        return {}
    try:
        messages = [
            SystemMessage(content="You are a medical text proofreader. Correct only spelling mistakes. Do not add, remove, or change anything else."),
            HumanMessage(content=state["extracted_text"]),
        ]
        result = groq_llm.invoke(messages)
        text = result.content.strip()
        return {
            "corrected_text": text,
            "events": [{"agent": 2, "result": text[:200] + "..."}],
        }
    except Exception as e:
        return {"error": f"Correction failed: {e}", "events": [{"agent": 2, "error": str(e)}]}


# ── Agent 3: Understanding (Groq) ────────────────────────────────────────────
def node_understanding(state: PrescriptionState) -> dict:
    if state.get("error"):
        return {}
    try:
        messages = [
            SystemMessage(content=(
                "You are a medical data extractor. Extract ONLY medically relevant information. "
                "Do NOT include patient name, address, phone number, or email. "
                "Format as a structured list: diagnosis, medications, dosage, observations, allergies, lab results."
            )),
            HumanMessage(content=state["corrected_text"]),
        ]
        result = groq_llm.invoke(messages)
        text = result.content.strip()
        return {
            "understood_text": text,
            "events": [{"agent": 3, "result": text[:200] + "..."}],
        }
    except Exception as e:
        return {"error": f"Understanding failed: {e}", "events": [{"agent": 3, "error": str(e)}]}


# ── Agent 4: FHIR Formatting (Groq) ──────────────────────────────────────────
def node_fhir(state: PrescriptionState) -> dict:
    if state.get("error"):
        return {}
    try:
        messages = [
            SystemMessage(content=(
                "You are a FHIR specialist. Convert medical text to FHIR JSON. "
                "Include only: diagnosis, medications, allergies, observations. "
                "Do NOT include patient name — use aadhaar as the only patient identifier. "
                "Respond with raw JSON only, no markdown fences."
            )),
            HumanMessage(content=state["understood_text"]),
        ]
        result = groq_llm.invoke(messages)
        fhir = result.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return {
            "fhir_json": fhir,
            "events": [{"agent": 4, "result": "FHIR format created"}],
        }
    except Exception as e:
        return {"error": f"FHIR failed: {e}", "events": [{"agent": 4, "error": str(e)}]}


# ── Agent 5: Graph DB (Groq generates Cypher, Python executes) ────────────────
def node_graph_db(state: PrescriptionState) -> dict:
    if state.get("error"):
        return {}
    aadhaar = state["aadhaar"]
    patient_exists = check_patient_exists(aadhaar)
    ensure_patient_node(aadhaar)

    action = "ADD new medical data to an EXISTING" if patient_exists else "link medical data to an existing"
    try:
        messages = [
            SystemMessage(content=(
                f"You are a Neo4j Cypher expert. Generate Cypher queries to {action} Patient node.\n"
                f"The Patient node has: aadhaar = \"{aadhaar}\".\n"
                "Use MATCH (p:Patient {aadhaar: \"" + aadhaar + "\"}) — NEVER create the Patient node again.\n"
                "CREATE new nodes (Medication, Diagnosis, Observation, Allergy, LabResult) and MERGE relationships.\n"
                "Use double quotes for all string values.\n"
                "Do NOT store patient name, address, or personal info.\n"
                "Output ONLY raw Cypher queries separated by semicolons. No explanations, no markdown."
            )),
            HumanMessage(content=state["understood_text"]),
        ]
        result = groq_llm.invoke(messages)
        raw_cypher = result.content.strip()
        if raw_cypher.startswith("```"):
            raw_cypher = "\n".join(
                line for line in raw_cypher.splitlines() if not line.startswith("```")
            )

        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                for query in raw_cypher.split(";"):
                    query = query.strip()
                    if query:
                        try:
                            session.run(query)
                        except Exception as qe:
                            print(f"Skipped query: {str(qe)[:150]}")
        finally:
            driver.close()

        return {
            "graph_queries": raw_cypher,
            "events": [{"agent": 5, "result": "Data stored in graph database"}],
        }
    except Exception as e:
        return {"error": f"Graph DB failed: {e}", "events": [{"agent": 5, "error": str(e)}]}


# ── Agent 6: Final Analysis (Groq) ────────────────────────────────────────────
def node_final_output(state: PrescriptionState) -> dict:
    if state.get("error"):
        return {}
    aadhaar = state["aadhaar"]
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
                    aadhaar=aadhaar,
                )
                patient_data = [record.data() for record in result]
        finally:
            driver.close()

        if not patient_data or all(r.get("n") is None for r in patient_data):
            summary = "Patient record created but no medical data linked yet. Upload a prescription to begin."
        else:
            formatted = safe_json_dumps(patient_data, indent=2)
            messages = [
                SystemMessage(content=(
                    "You are a clinical summariser. Based on patient graph data, provide:\n"
                    "1. Brief summary of condition\n"
                    "2. Current medications and dosage\n"
                    "3. Active diagnoses\n"
                    "4. Follow-up recommendations\n"
                    "Do NOT mention or infer patient name — use Aadhaar as identifier only."
                )),
                HumanMessage(content=f"Patient Data:\n{formatted}"),
            ]
            result = groq_llm.invoke(messages)
            summary = strip_markdown(result.content)

        return {
            "final_output": summary,
            "events": [{"agent": 6, "result": "Analysis complete"}],
        }
    except Exception as e:
        return {"error": f"Final output failed: {e}", "events": [{"agent": 6, "error": str(e)}]}


# ══════════════════════════════════════════════════════════════════════════════
# Build LangGraph
# ══════════════════════════════════════════════════════════════════════════════
def build_prescription_graph() -> StateGraph:
    graph = StateGraph(PrescriptionState)

    graph.add_node("ocr",           node_ocr)
    graph.add_node("correction",    node_correction)
    graph.add_node("understanding", node_understanding)
    graph.add_node("fhir",          node_fhir)
    graph.add_node("graph_db",      node_graph_db)
    graph.add_node("final",         node_final_output)

    graph.set_entry_point("ocr")
    graph.add_edge("ocr",           "correction")
    graph.add_edge("correction",    "understanding")
    graph.add_edge("understanding", "fhir")
    graph.add_edge("fhir",          "graph_db")
    graph.add_edge("graph_db",      "final")
    graph.add_edge("final",         END)

    return graph.compile()


prescription_pipeline = build_prescription_graph()


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI App
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(title="MediGraph Healthcare API", version="2.0.0")

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


# ── Pydantic Models ───────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    user_id: str
    password: str


class RegisterRequest(BaseModel):
    user_id: str
    password: str
    user_type: str


class LoginResponse(BaseModel):
    message: str
    user_type: str


# ── Auth Endpoints ────────────────────────────────────────────────────────────
@app.post("/api/auth/register")
async def register_user(request: RegisterRequest):
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
                    type=request.user_type,
                )
        finally:
            driver.close()

        return {"message": "Registration successful", "user_type": request.user_type}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/api/auth/login", response_model=LoginResponse)
async def login_user(request: LoginRequest):
    try:
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                result = session.run(
                    "MATCH (u:User {id: $id}) RETURN u.password as pwd, u.type as type",
                    id=request.user_id,
                )
                record = result.single()
                if not record:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                if record["pwd"] != hash_password(request.password):
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                return LoginResponse(message="Login successful", user_type=record["type"])
        finally:
            driver.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


# ── Prescription Processing (LangGraph pipeline) ─────────────────────────────
@app.post("/api/process-prescription")
async def process_prescription(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
):
    """Process prescription image through the 6-node LangGraph pipeline."""
    aadhaar = patient_id

    # ✅ Read file BEFORE the generator is created — prevents closed file I/O error
    image_bytes = await file.read()

    async def event_generator():
        try:
            # Emit "processing" status for each agent upfront
            for agent_num in range(1, 7):
                yield f"data: {json.dumps({'agent': agent_num, 'status': 'processing'})}\n\n"
                await asyncio.sleep(0.05)

            # Run the LangGraph pipeline in a thread so it doesn't block the event loop
            loop = asyncio.get_event_loop()
            final_state: PrescriptionState = await loop.run_in_executor(
                None,
                lambda: prescription_pipeline.invoke(
                    {
                        "image_bytes": image_bytes,
                        "aadhaar": aadhaar,
                        "extracted_text": "",
                        "corrected_text": "",
                        "understood_text": "",
                        "fhir_json": "",
                        "graph_queries": "",
                        "final_output": "",
                        "events": [],
                        "error": "",
                    }
                ),
            )

            # Stream back the per-agent results collected in state["events"]
            for event in final_state.get("events", []):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.1)

            if final_state.get("error"):
                yield f"data: {json.dumps({'error': final_state['error']})}\n\n"
            else:
                yield f"data: {json.dumps({'final': final_state['final_output']})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Patient Summary Endpoint ──────────────────────────────────────────────────
@app.get("/api/patient/{aadhaar}/summary")
async def get_patient_summary(aadhaar: str):
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
                    aadhaar=aadhaar,
                )
                data = [record.data() for record in result]
        finally:
            driver.close()

        if not data or all(r.get("n") is None for r in data):
            raise HTTPException(status_code=404, detail="Patient not found")

        medications, diagnoses = [], []
        for record in data:
            labels = record.get("labels", []) or []
            props  = record.get("props",  {}) or {}
            if "Medication" in labels:
                med = props.get("name", "Unknown")
                if "dosage" in props:
                    med += f" - {props['dosage']}"
                medications.append(med)
            elif "Diagnosis" in labels:
                diagnoses.append(props.get("condition", props.get("name", "Unknown")))

        messages = [
            SystemMessage(content=(
                "You are a clinical summariser. Provide: summary, medications, diagnoses, recommendations. "
                "Do not mention or infer patient name — use Aadhaar only."
            )),
            HumanMessage(content=f"Patient Data: {safe_json_dumps(data, indent=2)}"),
        ]
        result       = groq_llm.invoke(messages)
        summary_text = strip_markdown(result.content)

        return {
            "summary":         summary_text,
            "medications":     medications or ["No medications recorded"],
            "diagnoses":       diagnoses   or ["No diagnoses recorded"],
            "recommendations": summary_text,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ── Health / Root ─────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "MediGraph Healthcare API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)