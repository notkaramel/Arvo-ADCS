
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
import re

app = FastAPI(title="Language Context Extraction", version="0.1.0")

class Instruction(BaseModel):
    instruction: str

CLOUD_KEYWORDS = {
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud"],
    "azure": ["azure", "microsoft azure"],
    "digitalocean": ["digitalocean", "do droplet", "droplet"],
    "heroku": ["heroku"],
    "oracle": ["oci", "oracle cloud"],
    "hcloud": ["hetzner", "hetzner cloud"],
    "onprem": ["on-prem", "on prem", "onprem", "bare metal", "datacenter"]
}

DEPLOYMENT_TARGETS = {
    "containers": ["container", "containers", "docker", "compose", "podman"],
    "kubernetes": ["kubernetes", "k8s", "eks", "gke", "aks"],
    "serverless": ["serverless", "lambda", "cloud functions", "azure functions"],
    "vm": ["vm", "ec2", "compute engine", "droplet", "vmss"],
    "static_site": ["static site", "static hosting", "s3 website", "cloudfront", "netlify", "vercel"],
    "paas": ["elastic beanstalk", "app engine", "app service", "render.com", "heroku"]
}

DATABASES = {
    "postgres": ["postgres", "postgre", "rds postgres", "aurora postgres"],
    "mysql": ["mysql", "maria", "aurora mysql"],
    "sqlite": ["sqlite"],
    "mongodb": ["mongo", "mongodb", "documentdb"],
    "redis": ["redis", "elasticache"],
    "dynamodb": ["dynamodb"],
}

STORAGE = {
    "s3": ["s3", "object storage", "bucket"],
    "efs": ["efs", "nfs"],
    "ebs": ["ebs"],
    "gcs": ["gcs"],
    "blob": ["blob storage"],
}

NETWORKING = {
    "ingress": ["ingress", "alb", "nlb", "elb", "cloud load balancer", "application gateway"],
    "dns": ["route53", "dns", "cloud dns"],
    "vpc": ["vpc", "subnet", "security group", "nacl", "peering"],
    "cdn": ["cloudfront", "cdn", "cloud cdn", "azure cdn"],
}

CI_CD = ["github actions", "gitlab ci", "circleci", "argo", "argo cd", "flux", "jenkins", "travis"]

def find_keys(text: str, mapping: Dict[str, List[str]]) -> List[str]:
    res = []
    t = text.lower()
    for key, kws in mapping.items():
        if any(re.search(r"\b" + re.escape(kw) + r"\b", t) for kw in kws):
            res.append(key)
    return sorted(set(res))

def find_list(text: str, kws: List[str]) -> List[str]:
    t = text.lower()
    return sorted(set([kw for kw in kws if re.search(r"\b" + re.escape(kw) + r"\b", t)]))

@app.post("/extract")
def extract(inst: Instruction):
    t = inst.instruction.strip()
    providers = find_keys(t, CLOUD_KEYWORDS) or ["unspecified"]
    targets = find_keys(t, DEPLOYMENT_TARGETS)
    dbs = find_keys(t, DATABASES)
    storage = find_keys(t, STORAGE)
    networking = find_keys(t, NETWORKING)
    cicd = find_list(t, CI_CD)

    regions = re.findall(r"\b([a-z]{2}-[a-z]+-[0-9])\b", t, flags=re.IGNORECASE)  # e.g., us-east-1
    scaling = "auto" if re.search(r"\bauto-?scal", t, re.I) else ("manual" if "scale" in t.lower() else "unspecified")

    result = {
        "cloud_provider": providers,
        "deployment_targets": targets,
        "infrastructure": {
            "compute": "containers" if ("containers" in targets or "kubernetes" in targets) else ("serverless" if "serverless" in targets else ("vm" if "vm" in targets else "unspecified")),
            "container_orchestration": "kubernetes" if "kubernetes" in targets else ("compose" if "containers" in targets else None),
            "serverless": True if "serverless" in targets else False,
            "databases": dbs,
            "storage": storage,
            "networking": networking,
            "ci_cd": cicd,
        },
        "regions": regions or None,
        "scaling": scaling,
        "runtime_constraints": {
            "cost_optimized": bool(re.search(r"\bcost|budget|cheap|low\s*cost\b", t, re.I)),
            "high_availability": bool(re.search(r"\bha|high\s*availability|multi-az|multi region|multi-region\b", t, re.I)),
            "compliance": [m.group(0).lower() for m in re.finditer(r"\b(gdpr|hipaa|pci(?:-dss)?)\b", t, re.I)],
        },
        "additional_context": {
            "raw_instruction": t
        }
    }
    return result
