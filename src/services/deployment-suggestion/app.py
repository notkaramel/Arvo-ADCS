
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
import json

# Optional use of transformers; included as an optional helper if a model is available.
try:
    from transformers import pipeline
    _generator = pipeline("text-generation", model=os.getenv("HF_MODEL","gpt2"), device=-1)
except Exception:
    _generator = None

app = FastAPI(title="Deployment Suggestion", version="0.1.0")

class SuggestRequest(BaseModel):
    language_context: Dict[str, Any]
    codebase_context: Dict[str, Any]

@app.post("/suggest")
def suggest(req: SuggestRequest):
    lang = req.language_context or {}
    code = req.codebase_context or {}

    instr = lang.get("additional_context", {}).get("raw_instruction", "")

    arch = code.get("architecture", "")
    containerization = code.get("containerization", {})
    dockerfiles = containerization.get("dockerfile", False)
    compose = containerization.get("compose", False)
    k8s_hint = False

    # Heuristics to decide suggestion type
    if "kubernetes" in lang.get("deployment_targets", []) or "kubernetes" in instr.lower() or "minikube" in instr.lower():
        suggestion_type = "kubernetes-minikube"
        k8s_hint = True
    elif arch == "multi-microservices" or (isinstance(code.get("file_count",0), int) and code.get("file_count",0)>200) or (compose or (code.get("containerization",{}).get("compose"))):
        suggestion_type = "multi-microservice"
    elif dockerfiles and not compose:
        # There's at least a Dockerfile but no compose -> likely single container or single microservice
        suggestion_type = "single-container"
    else:
        # default fallback
        suggestion_type = "single-container"

    # Build suggestion sentences
    sentences = []
    if suggestion_type == "single-container":
        sentences.append("Recommend packaging the application as a single Docker container and deploying using Docker Compose or a single ECS/Fargate task.")
        sentences.append("Create a root-level Dockerfile (if missing) that builds the app, and a minimal docker-compose.yml that exposes the required ports and maps environment variables.")
        sentences.append("For quick local testing, `docker build` and `docker run` or `docker compose up` are sufficient; for production consider using ECS Fargate or a single-node Kubernetes deployment.")
    elif suggestion_type == "multi-microservice":
        sentences.append("Recommend maintaining multiple services, each with its own Dockerfile, orchestrated with docker-compose for local development and CI, and consider Kubernetes (EKS/AKS/GKE) for production.")
        sentences.append("Generate or enhance a docker-compose.yml that defines all discovered services, their build contexts, exposed ports, volumes, and networks. Ensure clear service names and health checks.")
        sentences.append("For deployment to AWS, consider EKS or a multi-service ECS setup; for simple setups, use docker-compose on EC2 or Docker on ECS with multiple tasks.")
    elif suggestion_type == "kubernetes-minikube":
        sentences.append("Recommend preparing the project for Kubernetes and testing locally with Minikube. Create Deployment and Service manifests for each container, and optionally a single Ingress resource.")
        sentences.append("Provide a `k8s/` directory with `deployment.yaml`, `service.yaml`, and `ingress.yaml` examples, plus a `Makefile` or script to build images and load them into Minikube.")
        sentences.append("For AWS production, map these manifests to EKS resources and use managed services for DB (RDS) and storage (EFS/S3).")
    else:
        sentences.append("General recommendation: containerize and provide a reproducible local orchestration strategy (docker-compose) and Kubernetes manifests for production-grade deployments.")

    suggestion_text = " ".join(sentences)

    # Optionally refine suggestion using a local HF model (if installed)
    if _generator is not None:
        try:
            gen = _generator(suggestion_text, max_length=256, do_sample=False)
            # generator returns list of dicts with 'generated_text'
            suggestion_text = gen[0].get("generated_text", suggestion_text)
        except Exception:
            pass

    structured = {
        "type": suggestion_type,
        "sentences": sentences,
        "suggestion_text": suggestion_text
    }

    return {"suggestion": structured}
