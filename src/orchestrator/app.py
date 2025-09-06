from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import os
import requests
import json

app = FastAPI(title="Orchestrator", version="0.2.0")

# Internal URLs
LANG_URL = os.getenv("LANGUAGE_CONTEXT_URL", "http://language-context:8001/extract")
CODE_URL = os.getenv("CODEBASE_CONTEXT_URL", "http://codebase-context:8002/extract")
SUGGESTION_URL = os.getenv("SUGGESTION_URL", "http://deployment-suggestion:8003/suggest")
CONTAINERIZE_URL = os.getenv("CONTAINERIZE_URL", "http://containerize-project:8004/apply")

@app.post("/analyze")
async def analyze(instruction: str = Form(...), repo_zip: UploadFile = File(...), generate_artifact: bool = Form(False)):
    # 1. Language context extraction
    lang_resp = requests.post(LANG_URL, data={"instruction": instruction})
    if lang_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="language-context service failed")
    language_context = lang_resp.json()
    
    # 2. Codebase context extraction
    code_files = {"repo_zip": (repo_zip.filename, await repo_zip.read(), "application/zip")}
    code_resp = requests.post(CODE_URL, files=code_files)
    if code_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="codebase-context service failed")
    codebase_context = code_resp.json()
    
    # 3. Deployment suggestion
    suggest_payload = {
        "language_context": language_context,
        "codebase_context": codebase_context
    }
    suggest_resp = requests.post(SUGGESTION_URL, json=suggest_payload)
    if suggest_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="deployment-suggestion service failed")
    deployment_suggestion = suggest_resp.json()
    
    # 4. Containerize project (optional)
    artifact_zip = None
    if generate_artifact:
        files = {"repo_zip": (repo_zip.filename, await repo_zip.read(), "application/zip")}
        data = {
            "suggestion_text": deployment_suggestion.get("suggestion", {}).get("suggestion_text", ""),
            "suggestion_type": deployment_suggestion.get("suggestion", {}).get("type", "")
        }
        cont_resp = requests.post(CONTAINERIZE_URL, data=data, files=files)
        if cont_resp.status_code == 200:
            artifact_zip = cont_resp.json().get("artifact_zip")
    
    return {
        "language_context": language_context,
        "codebase_context": codebase_context,
        "deployment_suggestion": deployment_suggestion,
        "artifact_zip": artifact_zip
    }
