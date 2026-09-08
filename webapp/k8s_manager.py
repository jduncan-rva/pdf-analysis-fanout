import os
import uuid
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("k8s_manager")

INGEST_IMAGE = os.environ.get("INGEST_IMAGE", "us-central1-docker.pkg.dev/gke-llm-testing-env/pdf-fanout-repo/pdf-ingest-job:latest")
ANALYSIS_IMAGE = os.environ.get("ANALYSIS_IMAGE", "us-central1-docker.pkg.dev/gke-llm-testing-env/pdf-fanout-repo/pdf-analysis-job:latest")
DATA_BUCKET = os.environ.get("DATA_BUCKET", "gke-llm-testing-env-pdf-data")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://pdf-webapp-service:8000")
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "default")

def get_k8s_batch_client():
    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        return client.BatchV1Api()
    except Exception as e:
        logger.warning(f"Could not load Kubernetes client: {e}. Running in standalone/mock mode.")
        return None

def trigger_ingest_job(gcs_uri: str, doc_id: Optional[str] = None) -> Dict[str, Any]:
    if not doc_id:
        # derive doc_id from gcs_uri or uuid
        clean_name = gcs_uri.split("/")[-1].replace(".pdf", "").replace(" ", "_")
        doc_id = f"{clean_name}_{uuid.uuid4().hex[:8]}"
        
    suffix = uuid.uuid4().hex[:6]
    clean_doc = doc_id.lower().replace('_', '-')[:36]
    job_name = f"ingest-{clean_doc}-{suffix}"
    
    batch_v1 = get_k8s_batch_client()
    if batch_v1 is None:
        logger.info(f"[MOCK] Spawning Ingest Job {job_name} for {gcs_uri}")
        return {"status": "dispatched_mock", "job_name": job_name, "doc_id": doc_id}

    from kubernetes import client
    
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=job_name,
            labels={"app": "pdf-ingest-job", "doc_id": doc_id}
        ),
        spec=client.V1JobSpec(
            backoff_limit=2,
            ttl_seconds_after_finished=3600,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "pdf-ingest-job"}),
                spec=client.V1PodSpec(
                    service_account_name="pdf-webapp-sa",
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="ingest",
                            image=INGEST_IMAGE,
                            env=[
                                client.V1EnvVar(name="GCS_URI", value=gcs_uri),
                                client.V1EnvVar(name="DOC_ID", value=doc_id),
                                client.V1EnvVar(name="DATA_BUCKET", value=DATA_BUCKET),
                                client.V1EnvVar(name="WEBAPP_URL", value=WEBAPP_URL),
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={"cpu": "500m", "memory": "512Mi"},
                                limits={"cpu": "1000m", "memory": "1Gi"}
                            )
                        )
                    ]
                )
            )
        )
    )
    
    try:
        response = batch_v1.create_namespaced_job(namespace=K8S_NAMESPACE, body=job)
        logger.info(f"Created Ingest K8s Job: {response.metadata.name}")
        return {"status": "created", "job_name": response.metadata.name, "doc_id": doc_id}
    except Exception as e:
        logger.error(f"Failed to create Ingest K8s Job: {e}")
        raise e

def trigger_analysis_job(doc_id: str, gcs_uri: str) -> Dict[str, Any]:
    suffix = uuid.uuid4().hex[:6]
    clean_doc = doc_id.lower().replace('_', '-')[:36]
    job_name = f"analyze-{clean_doc}-{suffix}"
    
    batch_v1 = get_k8s_batch_client()
    if batch_v1 is None:
        logger.info(f"[MOCK] Spawning Analysis Job {job_name} for doc {doc_id}")
        return {"status": "dispatched_mock", "job_name": job_name, "doc_id": doc_id}

    from kubernetes import client
    
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=job_name,
            labels={"app": "pdf-analysis-job", "doc_id": doc_id}
        ),
        spec=client.V1JobSpec(
            backoff_limit=1,
            ttl_seconds_after_finished=7200,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "pdf-analysis-job"}),
                spec=client.V1PodSpec(
                    service_account_name="pdf-webapp-sa",
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="analysis",
                            image=ANALYSIS_IMAGE,
                            env=[
                                client.V1EnvVar(name="DOC_ID", value=doc_id),
                                client.V1EnvVar(name="GCS_URI", value=gcs_uri),
                                client.V1EnvVar(name="DATA_BUCKET", value=DATA_BUCKET),
                                client.V1EnvVar(name="WEBAPP_URL", value=WEBAPP_URL),
                                client.V1EnvVar(name="GOOGLE_GENAI_USE_VERTEXAI", value="true"),
                                client.V1EnvVar(name="GOOGLE_CLOUD_PROJECT", value=os.environ.get("GOOGLE_CLOUD_PROJECT", "gke-llm-testing-env")),
                                client.V1EnvVar(name="GOOGLE_CLOUD_LOCATION", value=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")),
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={"cpu": "1000m", "memory": "2Gi"},
                                limits={"cpu": "2000m", "memory": "4Gi"}
                            )
                        )
                    ]
                )
            )
        )
    )
    
    try:
        response = batch_v1.create_namespaced_job(namespace=K8S_NAMESPACE, body=job)
        logger.info(f"Created Analysis K8s Job: {response.metadata.name}")
        return {"status": "created", "job_name": response.metadata.name, "doc_id": doc_id}
    except Exception as e:
        logger.error(f"Failed to create Analysis K8s Job: {e}")
        raise e
