import os
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import database
import k8s_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdf_webapp")

app = FastAPI(title="PDF Analysis & Ingestion Fanout System")

# Mount templates & static files
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")
static_dir = os.path.join(current_dir, "static")

os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Init database on startup
@app.on_event("startup")
def startup_event():
    database.init_db()
    logger.info("Database initialized successfully.")

# Pydantic Request Models
class IngestTriggerRequest(BaseModel):
    gcs_uri: str
    doc_id: Optional[str] = None

class IngestWebhookPayload(BaseModel):
    doc_id: str
    filename: str
    gcs_uri: str
    page_count: int
    institution: Optional[str] = None
    doc_date: Optional[str] = None
    account_numbers: Optional[str] = None
    raw_metadata_uri: str
    searchable_text: str

class IngestErrorPayload(BaseModel):
    doc_id: Optional[str] = None
    gcs_uri: str
    error_message: str
    traceback: Optional[str] = None

class AnalysisWebhookPayload(BaseModel):
    doc_id: str
    summary: str
    structured_json: Dict[str, Any]
    report_gcs_uri: Optional[str] = None

class AnalysisErrorPayload(BaseModel):
    doc_id: str
    error_message: str
    traceback: Optional[str] = None


# --- Web UI Routes ---

@app.get("/", response_class=HTMLResponse)
async def index_view(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- API Routes: Search & Documents ---

@app.get("/api/search")
async def search_docs(q: str = "", limit: int = 50):
    results = database.search_documents_bm25(q, limit=limit)
    return {"query": q, "count": len(results), "results": results}

@app.get("/api/docs")
async def list_docs(limit: int = 50):
    results = database.list_recent_documents(limit=limit)
    return {"count": len(results), "results": results}

@app.get("/api/docs/{doc_id}")
async def get_doc(doc_id: str):
    doc = database.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

# --- API Routes: Ingest Workflows ---

@app.post("/api/ingest/trigger")
async def trigger_ingest(payload: IngestTriggerRequest):
    """Triggered by Cloud Function or manual upload"""
    try:
        res = k8s_manager.trigger_ingest_job(payload.gcs_uri, payload.doc_id)
        return {"status": "success", "data": res}
    except Exception as e:
        logger.exception("Failed to trigger ingest job")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest/webhook")
async def ingest_webhook(payload: IngestWebhookPayload):
    """Ingest K8s Job POSTs its results here"""
    try:
        database.upsert_document_ingest(
            doc_id=payload.doc_id,
            filename=payload.filename,
            gcs_uri=payload.gcs_uri,
            page_count=payload.page_count,
            institution=payload.institution,
            doc_date=payload.doc_date,
            account_numbers=payload.account_numbers,
            raw_metadata_uri=payload.raw_metadata_uri,
            searchable_text=payload.searchable_text
        )
        logger.info(f"Ingest completed for doc {payload.doc_id}")
        return {"status": "ok", "doc_id": payload.doc_id}
    except Exception as e:
        logger.exception(f"Error processing ingest webhook for {payload.doc_id}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest/error")
async def ingest_error(payload: IngestErrorPayload):
    """Ingest K8s Job POSTs failure diagnostic here"""
    database.record_ingest_error(
        doc_id=payload.doc_id,
        gcs_uri=payload.gcs_uri,
        error_message=payload.error_message,
        traceback=payload.traceback
    )
    logger.warning(f"Recorded ingest error for {payload.gcs_uri}: {payload.error_message}")
    return {"status": "recorded"}

# --- API Routes: Analysis Workflows ---

@app.post("/api/analyze/trigger/{doc_id}")
async def trigger_analysis(doc_id: str):
    """User clicks 'Analyze' in UI"""
    doc = database.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Set status to ANALYZING
    database.set_document_status(doc_id, "ANALYZING")
    
    try:
        res = k8s_manager.trigger_analysis_job(doc_id, doc["gcs_uri"])
        return {"status": "success", "data": res}
    except Exception as e:
        database.record_analysis_error(doc_id, f"Failed to spawn analysis job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze/webhook")
async def analyze_webhook(payload: AnalysisWebhookPayload):
    """Analysis K8s Job (Antigravity SDK) POSTs results here"""
    import json
    try:
        database.record_analysis_result(
            doc_id=payload.doc_id,
            summary=payload.summary,
            structured_json=json.dumps(payload.structured_json),
            report_gcs_uri=payload.report_gcs_uri
        )
        logger.info(f"Analysis successfully recorded for doc {payload.doc_id}")
        return {"status": "ok", "doc_id": payload.doc_id}
    except Exception as e:
        logger.exception(f"Error processing analysis webhook for {payload.doc_id}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze/error")
async def analyze_error(payload: AnalysisErrorPayload):
    """Analysis K8s Job POSTs error here"""
    database.record_analysis_error(
        doc_id=payload.doc_id,
        error_message=payload.error_message,
        traceback=payload.traceback
    )
    logger.warning(f"Recorded analysis error for {payload.doc_id}: {payload.error_message}")
    return {"status": "recorded"}
