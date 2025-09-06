
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os, requests

LANG_URL = os.getenv("LANGUAGE_CONTEXT_URL", "http://language-context:8001/extract")
CODE_URL = os.getenv("CODEBASE_CONTEXT_URL", "http://codebase-context:8002/extract")

app = FastAPI(title="Deploy Context Orchestrator", version="0.1.0")

class AnalyzeResponse(BaseModel):
    language_context: Dict[str, Any]
    codebase_context: Dict[str, Any]
    recommendations: Dict[str, Any]

def recommend(lang_ctx: Dict[str, Any], code_ctx: Dict[str, Any]) -> Dict[str, Any]:
    providers = lang_ctx.get("cloud_provider", [])
    targets = lang_ctx.get("deployment_targets", [])
    containerized = code_ctx.get("containerization", {}).get("dockerfile") or ("containers" in targets or "kubernetes" in targets)
    langs = list((code_ctx.get("languages") or {}).keys())

    suggestions: Dict[str, Any] = {"targets": [], "databases": [], "networking": [], "storage": [], "ci_cd": []}

    # Provider-specific compute
    if "aws" in providers or "unspecified" in providers:
        if containerized:
            suggestions["targets"].append("AWS ECS on Fargate")
            if "kubernetes" in targets:
                suggestions["targets"].append("AWS EKS (managed Kubernetes)")
        elif "serverless" in targets or ("Python" in langs or "JavaScript" in langs):
            suggestions["targets"].append("AWS Lambda + API Gateway")
        else:
            suggestions["targets"].append("EC2 Auto Scaling Group")

        # Databases
        dbs = lang_ctx.get("infrastructure", {}).get("databases", [])
        if "postgres" in dbs:
            suggestions["databases"].append("Amazon RDS for PostgreSQL")
        if "mysql" in dbs:
            suggestions["databases"].append("Amazon RDS for MySQL/Aurora")
        if "mongodb" in dbs:
            suggestions["databases"].append("Amazon DocumentDB")
        if not suggestions["databases"] and ("PostgreSQL" in langs or "JavaScript" in langs):
            suggestions["databases"].append("Amazon RDS (choose engine)")

        # Storage/CDN
        if "static_site" in targets:
            suggestions["storage"].append("S3 + CloudFront")
        elif containerized:
            suggestions["storage"].append("S3 for assets; EFS/EBS for stateful needs")

        # Networking
        suggestions["networking"].append("ALB/NLB depending on protocol")
        suggestions["networking"].append("Route 53 for DNS")
        suggestions["ci_cd"].append("GitHub Actions -> OIDC to AWS; or AWS CodePipeline")

    # Basic non-AWS fallbacks
    if "gcp" in providers:
        suggestions["targets"].append("GKE or Cloud Run")
        suggestions["databases"].append("Cloud SQL (Postgres/MySQL)")
        suggestions["storage"].append("GCS + Cloud CDN")
        suggestions["networking"].append("Cloud Load Balancing")
        suggestions["ci_cd"].append("Cloud Build or GitHub Actions")

    if "azure" in providers:
        suggestions["targets"].append("AKS or Azure Container Apps")
        suggestions["databases"].append("Azure Database for PostgreSQL/MySQL")
        suggestions["storage"].append("Azure Blob Storage + CDN")
        suggestions["networking"].append("Azure Application Gateway/Front Door")
        suggestions["ci_cd"].append("GitHub Actions or Azure DevOps")

    # Frontend hint
    app_types = code_ctx.get("application_type", [])
    if "frontend" in app_types:
        suggestions.setdefault("frontend", []).append("Static hosting + CDN (e.g., S3+CloudFront or equivalent)")

    # Security/ops
    runtime = lang_ctx.get("runtime_constraints", {})
    if runtime.get("high_availability"):
        suggestions.setdefault("resilience", []).append("Multi-AZ and health checks; DB read replicas")
    if runtime.get("cost_optimized"):
        suggestions.setdefault("cost", []).append("Use Fargate Spot / Graviton where applicable")

    return suggestions

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    instruction: str = Form(...),
    repo_url: Optional[str] = Form(default=None),
    repo_zip: Optional[UploadFile] = File(default=None),
):
    # Call language-context
    lang_resp = requests.post(LANG_URL, json={"instruction": instruction})
    lang_resp.raise_for_status()
    language_context = lang_resp.json()

    # Call codebase-context
    files = None
    data = {"repo_url": (None, repo_url)} if repo_url else {}
    if repo_zip is not None:
        files = {"repo_zip": (repo_zip.filename, await repo_zip.read(), repo_zip.content_type or "application/zip")}
        code_resp = requests.post(CODE_URL, data={}, files=files)
    else:
        code_resp = requests.post(CODE_URL, data=data)

    code_resp.raise_for_status()
    codebase_context = code_resp.json()

    recs = recommend(language_context, codebase_context)

    return {
        "language_context": language_context,
        "codebase_context": codebase_context,
        "recommendations": recs
    }
