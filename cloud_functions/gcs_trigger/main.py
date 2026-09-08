import os
import logging
import requests
import functions_framework
from cloudevents.http import CloudEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gcs_trigger")

WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://pdf-webapp-service:8000")

@functions_framework.cloud_event
def handle_pdf_upload(cloud_event: CloudEvent):
    """
    Triggered by GCS object finalized event (Eventarc / Cloud Storage)
    """
    data = cloud_event.data
    bucket_name = data.get("bucket")
    file_name = data.get("name")

    if not bucket_name or not file_name:
        logger.warning(f"Malformed event data: {data}")
        return

    # Process only PDF files
    if not file_name.lower().endswith(".pdf"):
        logger.info(f"Skipping non-PDF object: {file_name}")
        return

    gcs_uri = f"gs://{bucket_name}/{file_name}"
    logger.info(f"New PDF detected: {gcs_uri}. Triggering ingestion pipeline via Webapp...")

    payload = {
        "gcs_uri": gcs_uri
    }

    try:
        url = f"{WEBAPP_URL}/api/ingest/trigger"
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        logger.info(f"Successfully triggered ingest for {gcs_uri}: {resp.json()}")
    except Exception as e:
        logger.error(f"Failed to trigger ingest for {gcs_uri}: {e}")
        raise e
