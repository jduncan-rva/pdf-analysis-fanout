import os
import sys
import re
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List

import fitz  # PyMuPDF
import requests
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_job")

GCS_URI = os.environ.get("GCS_URI")
DOC_ID = os.environ.get("DOC_ID")
DATA_BUCKET = os.environ.get("DATA_BUCKET")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://pdf-webapp-service:8000")

def parse_gcs_uri(uri: str):
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {uri}")
    parts = uri[5:].split("/", 1)
    bucket_name = parts[0]
    blob_name = parts[1] if len(parts) > 1 else ""
    return bucket_name, blob_name

def extract_pdf_data(pdf_bytes: bytes) -> Dict[str, Any]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    
    pages_text = []
    full_text_list = []
    
    for page_num in range(page_count):
        page = doc[page_num]
        text = page.get_text("text")
        pages_text.append({
            "page_number": page_num + 1,
            "text": text,
            "char_count": len(text)
        })
        full_text_list.append(text)
        
    full_text = "\n\n".join(full_text_list)
    first_page_text = pages_text[0]["text"] if pages_text else ""
    
    # Fast regex-based heuristic extraction
    institutions = [
        "Chase", "JPMorgan", "Wells Fargo", "Bank of America", "Citibank", 
        "PNC", "US Bank", "Capital One", "TD Bank", "Fidelity", "Charles Schwab", 
        "Vanguard", "Internal Revenue Service", "IRS", "Department of the Treasury"
    ]
    detected_institution = None
    for inst in institutions:
        if re.search(r'\b' + re.escape(inst) + r'\b', first_page_text, re.IGNORECASE):
            detected_institution = inst
            break

    # Date regex matching (MM/DD/YYYY, YYYY-MM-DD, Month DD, YYYY)
    date_patterns = [
        r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b',
        r'\b(?:19|20)\d{2}[/-](?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (?:0?[1-9]|[12]\d|3[01]),? (?:19|20)\d{2}\b'
    ]
    detected_dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, first_page_text, re.IGNORECASE)
        detected_dates.extend(matches)

    # Account number pattern matching
    account_patterns = [
        r'(?:Account|Acct|Acc)[\s#.:]+([A-Z0-9-]{4,18})',
        r'(?:Account Number)[\s#.:]+([A-Z0-9-]{4,18})',
        r'(?:Card ending in|ending in)[\s#.:]+([0-9]{4})'
    ]
    detected_accounts = []
    for pattern in account_patterns:
        matches = re.findall(pattern, first_page_text, re.IGNORECASE)
        detected_accounts.extend(matches)

    return {
        "page_count": page_count,
        "institution": detected_institution,
        "doc_date": detected_dates[0] if detected_dates else None,
        "account_numbers": ", ".join(list(dict.fromkeys(detected_accounts))) if detected_accounts else None,
        "searchable_text": full_text,
        "pages": pages_text
    }

def main():
    if not GCS_URI:
        logger.error("GCS_URI environment variable is required.")
        sys.exit(1)
        
    doc_id = DOC_ID or GCS_URI.split("/")[-1].replace(".pdf", "")
    filename = GCS_URI.split("/")[-1]
    
    logger.info(f"Starting Ingest Job for {GCS_URI} (doc_id={doc_id})")
    
    storage_client = storage.Client()
    
    try:
        # 1. Download PDF from GCS
        src_bucket, src_blob = parse_gcs_uri(GCS_URI)
        bucket = storage_client.bucket(src_bucket)
        blob = bucket.blob(src_blob)
        
        pdf_bytes = blob.download_as_bytes()
        logger.info(f"Downloaded {len(pdf_bytes)} bytes from {GCS_URI}")
        
        # 2. Extract text and metadata with PyMuPDF
        extracted = extract_pdf_data(pdf_bytes)
        logger.info(f"Extracted {extracted['page_count']} pages from {filename}")
        
        # 3. Save extracted metadata JSON to DATA_BUCKET
        raw_metadata_uri = ""
        if DATA_BUCKET:
            out_blob_name = f"extracted_metadata/{doc_id}.json"
            out_bucket = storage_client.bucket(DATA_BUCKET)
            out_blob = out_bucket.blob(out_blob_name)
            out_blob.upload_from_string(
                json.dumps(extracted, indent=2),
                content_type="application/json"
            )
            raw_metadata_uri = f"gs://{DATA_BUCKET}/{out_blob_name}"
            logger.info(f"Saved raw metadata JSON to {raw_metadata_uri}")
            
        # 4. POST result to Webapp Webhook
        webhook_payload = {
            "doc_id": doc_id,
            "filename": filename,
            "gcs_uri": GCS_URI,
            "page_count": extracted["page_count"],
            "institution": extracted["institution"],
            "doc_date": extracted["doc_date"],
            "account_numbers": extracted["account_numbers"],
            "raw_metadata_uri": raw_metadata_uri,
            "searchable_text": extracted["searchable_text"]
        }
        
        webhook_url = f"{WEBAPP_URL}/api/ingest/webhook"
        logger.info(f"Posting results to {webhook_url}")
        resp = requests.post(webhook_url, json=webhook_payload, timeout=30)
        resp.raise_for_status()
        logger.info(f"Successfully ingested doc {doc_id}")
        
    except Exception as e:
        logger.exception(f"Ingest failed for {GCS_URI}")
        error_payload = {
            "doc_id": doc_id,
            "gcs_uri": GCS_URI,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }
        try:
            requests.post(f"{WEBAPP_URL}/api/ingest/error", json=error_payload, timeout=10)
        except Exception as post_err:
            logger.error(f"Failed to post error webhook: {post_err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
