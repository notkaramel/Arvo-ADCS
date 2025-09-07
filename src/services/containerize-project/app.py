
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import Optional, Dict, Any
import tempfile, zipfile, os, shutil, pathlib, yaml, io, uuid

app = FastAPI(title="Containerize Project", version="0.1.0")

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

def simple_dockerfile_for_language(lang_names):
    # Very small heuristics for common languages
    if not lang_names:
        return "FROM alpine:3.18\nCMD [\"/bin/sh\"]\n"
    primary = lang_names[0].lower()
    if "python" in primary:
        return "FROM python:3.12-slim\nWORKDIR /app\nCOPY . /app\nRUN pip install --no-cache-dir -r requirements.txt || true\nCMD [\"python\", \"main.py\"]\n"
    if "node" in primary or "javascript" in primary or "typescript" in primary:
        return "FROM node:20-alpine\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install || true\nCOPY . .\nCMD [\"npm\", \"start\"]\n"
    if "go" in primary:
        return "FROM golang:1.21-alpine\nWORKDIR /app\nCOPY . .\nRUN go build -o app ./...\nCMD [\"/app/app\"]\n"
    return "FROM alpine:3.18\nCOPY . /app\nCMD [\"/bin/sh\"]\n"

@app.post("/")
async def apply(suggestion_text: Optional[str] = Form(None),
                suggestion_type: Optional[str] = Form(None),
                repo_zip: Optional[UploadFile] = File(None)):
    if repo_zip is None:
        raise HTTPException(status_code=400, detail="repo_zip is required")

    # Save and extract zip
    tmpdir = tempfile.mkdtemp(prefix="repo_")
    try:
        zip_path = os.path.join(tmpdir, repo_zip.filename)
        with open(zip_path, "wb") as f:
            f.write(await repo_zip.read())
        extract_dir = os.path.join(tmpdir, "repo")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(extract_dir)

        # Inspect repo to decide actions
        files = []
        for base, _, fnames in os.walk(extract_dir):
            for fn in fnames:
                files.append(os.path.join(base, fn))

        # detect existing dockerfiles
        dockerfiles = [p for p in files if os.path.basename(p).lower() == "dockerfile"]
        compose_files = [p for p in files if os.path.basename(p).lower() in ("docker-compose.yml","docker-compose.yaml","compose.yml","compose.yaml")]

        # Default behavior: create artifacts in a new folder `generated_artifacts/`
        gen_dir = os.path.join(tmpdir, "generated_artifacts")
        os.makedirs(gen_dir, exist_ok=True)

        # Create actions based on suggestion_type
        if suggestion_type == "kubernetes-minikube" or (suggestion_text and "minikube" in suggestion_text.lower()):
            # Create k8s manifests + Makefile
            k8s_dir = os.path.join(gen_dir, "k8s")
            os.makedirs(k8s_dir, exist_ok=True)
            deployment_yaml = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name":"app-deployment"},
                "spec": {
                    "replicas": 1,
                    "selector":{"matchLabels":{"app":"app"}},
                    "template":{"metadata":{"labels":{"app":"app"}},
                    "spec":{"containers":[{"name":"app","image":"app-image:latest","ports":[{"containerPort":8000}]}]}
                    }
                }
            }
            service_yaml = {
                "apiVersion":"v1",
                "kind":"Service",
                "metadata":{"name":"app-service"},
                "spec":{"selector":{"app":"app"},"ports":[{"protocol":"TCP","port":80,"targetPort":8000}],"type":"NodePort"}
            }
            write_file(os.path.join(k8s_dir,"deployment.yaml"), yaml.safe_dump(deployment_yaml))
            write_file(os.path.join(k8s_dir,"service.yaml"), yaml.safe_dump(service_yaml))
            write_file(os.path.join(gen_dir,"README.md"), "Use `minikube image build -t app-image:latest .` and `kubectl apply -f k8s/` to test locally.\n")
        elif suggestion_type == "multi-microservice":
            # If multiple Dockerfiles exist, create docker-compose listing them. Otherwise, try to create a Dockerfile per folder with obvious entry points.
            comp = {"version":"3.9","services":{}}
            if dockerfiles:
                # Make each Dockerfile's directory a service
                for df in dockerfiles:
                    service_name = os.path.basename(os.path.dirname(df)) or "service"
                    reldir = os.path.relpath(os.path.dirname(df), extract_dir)
                    comp["services"][service_name] = {"build":{"context": "./" + reldir}, "ports":[]}
                write_file(os.path.join(gen_dir,"docker-compose.yml"), yaml.safe_dump(comp))
            else:
                # attempt simple single service compose as fallback
                comp["services"]["app"] = {"build":{"context":"./"}, "ports":["8000:8000"]}
                write_file(os.path.join(gen_dir,"docker-compose.yml"), yaml.safe_dump(comp))
            write_file(os.path.join(gen_dir,"README.md"), "docker-compose generated for multi-microservice local orchestration.\n")
        else:
            # single-container: ensure root Dockerfile exists in generated artifacts
            # detect primary language from common files
            lang = None
            for p in files:
                if p.endswith("requirements.txt"):
                    lang = "python"
                    break
                if p.endswith("package.json"):
                    lang = "node"
                    break
                if p.endswith("go.mod"):
                    lang = "go"
                    break
            dockerfile_content = simple_dockerfile_for_language([lang] if lang else [])
            write_file(os.path.join(gen_dir,"Dockerfile"), dockerfile_content)
            compose = {
                "version": "3.9",
                "services": {
                    "app": {
                        "build": {"context": "./"},
                        "ports": ["8000:8000"],
                        "environment": ["ENV=production"]
                    }
                }
            }
            write_file(os.path.join(gen_dir,"docker-compose.yml"), yaml.safe_dump(compose))
            write_file(os.path.join(gen_dir,"README.md"), "Generated simple Dockerfile + docker-compose for single-container deployment.\n")

        # create zip artifact
        artifact_path = os.path.join(tmpdir, f"artifact_{uuid.uuid4().hex}.zip")
        with zipfile.ZipFile(artifact_path, "w", zipfile.ZIP_DEFLATED) as z:
            for base, dirs, fnames in os.walk(gen_dir):
                for fn in fnames:
                    full = os.path.join(base, fn)
                    rel = os.path.relpath(full, gen_dir)
                    z.write(full, rel)

        # return artifact as downloadable file path (we'll save to /mnt/data so user can download)
        out_path = os.path.join("/mnt/data", os.path.basename(artifact_path))
        shutil.copyfile(artifact_path, out_path)
        return {"artifact_zip": out_path, "message":"artifact created"}
    finally:
        # don't delete tmpdir so the artifact remains available for debugging
        pass
