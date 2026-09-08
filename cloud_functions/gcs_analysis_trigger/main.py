import os
import logging
import requests
import functions_framework
from cloudevents.http import CloudEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analysis_trigger")

WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://pdf-webapp-service:8000")

@functions_framework.cloud_event
def handle_metadata_upload(cloud_event: CloudEvent):
    """
    Triggered by GCS object finalized in data bucket under extracted_metadata/
    """
    data = cloud_event.data
    bucket_name = data.get("bucket")
    file_name = data.get("name")

    if not bucket_name or not file_name:
        logger.warning(f"Malformed event data: {data}")
        return

    # Trigger only for extracted_metadata/*.json
    if not file_name.startswith("extracted_metadata/") or not file_name.endswith(".json"):
        logger.info(f"Skipping non-metadata file: {file_name}")
        return

    doc_id = os.path.basename(file_name).replace(".json", "")
    logger.info(f"New extracted metadata detected for doc {doc_id} in gs://{bucket_name}/{file_name}. Triggering deep analysis...")

    try:
        url = f"{WEBAPP_URL}/api/analyze/trigger/{doc_id}"
        resp = requests.post(url, timeout=15)
        resp.raise_for_status()
        logger.info(f"Successfully triggered analysis for doc {doc_id}: {resp.json()}")
    except Exception as e:
        logger.error(f"Failed to trigger analysis for doc {doc_id}: {e}")
        raise e
