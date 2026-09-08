import os
import sys
import json
import logging
import traceback
from typing import List, Optional, Dict, Any

import fitz  # PyMuPDF
import requests
from pydantic import BaseModel, Field
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("analysis_job")

DOC_ID = os.environ.get("DOC_ID")
GCS_URI = os.environ.get("GCS_URI")
DATA_BUCKET = os.environ.get("DATA_BUCKET")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://pdf-webapp-service:8000")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Structured Pydantic Schema for Deep Semantic Extraction
class TransactionItem(BaseModel):
    date: Optional[str] = Field(description="Transaction date (YYYY-MM-DD or MM/DD/YYYY)")
    description: str = Field(description="Full narrative description including multi-line notes")
    amount: float = Field(description="Transaction amount (negative for debits/withdrawals, positive for deposits)")
    running_balance: Optional[float] = Field(description="Account balance after this transaction, if present")
    category_hint: Optional[str] = Field(description="Inferred category e.g. Payroll, Wire, Fee, Retail, Utility")

class KeyValueField(BaseModel):
    field_label: str = Field(description="Exact label or field header on the form/document")
    field_value: str = Field(description="Bound value extracted for this label")
    page_number: int = Field(description="1-indexed page where this field was found")

class DeepDocumentAnalysis(BaseModel):
    document_type: str = Field(description="E.g. Bank Statement, Tax Form W2/1040, Invoice, Loan Application, Paystub")
    institution_or_issuer: Optional[str] = Field(description="Issuing organization or financial institution")
    account_holder_name: Optional[str] = Field(description="Name of the account holder, borrower, or taxpayer")
    account_identifier: Optional[str] = Field(description="Masked or full account / routing / EIN / SSN number")
    statement_period: Optional[str] = Field(description="Date range or tax year")
    executive_summary: str = Field(description="High-level narrative summary of the document contents, key findings, and anomalies")
    key_value_pairs: List[KeyValueField] = Field(default_factory=list, description="All 2D form key-value pairs extracted")
    transactions: List[TransactionItem] = Field(default_factory=list, description="All itemized line items or transactions")
    anomalies_or_flags: List[str] = Field(default_factory=list, description="Any red flags, unusual fees, or discrepancies found")

def parse_gcs_uri(uri: str):
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {uri}")
    parts = uri[5:].split("/", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")

def render_pdf_to_images(pdf_bytes: bytes) -> List[bytes]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    # Limit max pages for LLM context to top 10 pages if very large
    max_pages = min(len(doc), 10)
    for page_num in range(max_pages):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        images.append(img_bytes)
    return images

def run_multimodal_extraction(images: List[bytes]) -> DeepDocumentAnalysis:
    """Invokes Gemini Multimodal Vision with Structured Output Schema"""
    from google import genai
    from google.genai import types

    # Initialize Gemini client (uses Vertex AI in GKE or GEMINI_API_KEY)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID") or "gke-llm-testing-env"
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client(vertexai=True, project=project, location=location)

    contents = [
        "You are an expert financial forensic analyst and document understanding agent.",
        "Perform a comprehensive semantic extraction over the attached document pages.",
        "Ensure all multi-line transaction rows are accurately bound, and all 2D key-value form fields are mapped correctly.",
    ]

    for idx, img_bytes in enumerate(images):
        contents.append(f"--- Page {idx + 1} ---")
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DeepDocumentAnalysis,
            temperature=0.1,
        ),
    )

    result_data = json.loads(response.text)
    return DeepDocumentAnalysis(**result_data)

def main():
    if not DOC_ID or not GCS_URI:
        logger.error("DOC_ID and GCS_URI environment variables are required.")
        sys.exit(1)

    logger.info(f"Starting Deep Analysis Job for doc {DOC_ID} ({GCS_URI})")
    storage_client = storage.Client()

    try:
        # 1. Download PDF from GCS
        src_bucket, src_blob = parse_gcs_uri(GCS_URI)
        bucket = storage_client.bucket(src_bucket)
        blob = bucket.blob(src_blob)
        pdf_bytes = blob.download_as_bytes()
        logger.info(f"Downloaded {len(pdf_bytes)} bytes from {GCS_URI}")

        # 2. Render PDF pages into images for vision reasoning
        images = render_pdf_to_images(pdf_bytes)
        logger.info(f"Rendered {len(images)} pages into images for vision analysis")

        # 3. Run multimodal semantic extraction
        analysis_result = run_multimodal_extraction(images)
        analysis_dict = analysis_result.model_dump()
        logger.info("Successfully executed multimodal reasoning model.")

        # 4. Save analysis report JSON to DATA_BUCKET
        report_gcs_uri = ""
        if DATA_BUCKET:
            out_blob_name = f"analysis_reports/{DOC_ID}.json"
            out_bucket = storage_client.bucket(DATA_BUCKET)
            out_blob = out_bucket.blob(out_blob_name)
            out_blob.upload_from_string(
                json.dumps(analysis_dict, indent=2),
                content_type="application/json"
            )
            report_gcs_uri = f"gs://{DATA_BUCKET}/{out_blob_name}"
            logger.info(f"Saved analysis report to {report_gcs_uri}")

        # 5. POST result to Webapp Webhook
        webhook_payload = {
            "doc_id": DOC_ID,
            "summary": analysis_result.executive_summary,
            "structured_json": analysis_dict,
            "report_gcs_uri": report_gcs_uri
        }

        webhook_url = f"{WEBAPP_URL}/api/analyze/webhook"
        logger.info(f"Posting analysis results to {webhook_url}")
        resp = requests.post(webhook_url, json=webhook_payload, timeout=30)
        resp.raise_for_status()
        logger.info(f"Successfully posted analysis for {DOC_ID}")

    except Exception as e:
        logger.exception(f"Deep Analysis failed for {DOC_ID}")
        error_payload = {
            "doc_id": DOC_ID,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }
        try:
            requests.post(f"{WEBAPP_URL}/api/analyze/error", json=error_payload, timeout=10)
        except Exception as post_err:
            logger.error(f"Failed to post error webhook: {post_err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
