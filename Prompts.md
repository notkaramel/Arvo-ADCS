Prompts used to generate codes. Models are linked to the prompt.

- Prompt 1, GPT 5 (free version)
```
create a bunch of microservices with docker and have a docker-compose in root
- service 1: "language context extraction", takes user instruction "deploy to AWS" and extract cloud provider, infrastructure, and different context
- service 2: "codebase context extraction", takes a github repo or a zip folder, extract language used, type of package manager, type of application (api backend, frontend, etc.), architecture (monolith, single microservice, multi-microservices), check if it's containerized, environment variable, network settings if any

Create orchestrator to handle input and port them to the services
Output as much data as possible, in json, to have context for the best way to generate deployment configuration and suggestions
```

Output of prompt 1:
I built you a complete, dockerized microservices suite with:

* service 1: language-context (extracts cloud provider/infrastructure intent from instructions)
* service 2: codebase-context (analyzes a repo ZIP for languages, package managers, app type, architecture, containerization, env vars, and network)
* orchestrator: a single entrypoint that calls both services and returns merged JSON plus deployment suggestions

Download it here: [deploy-context-suite.zip](sandbox:/mnt/data/deploy-context-suite.zip)

### How to run

```bash
unzip deploy-context-suite.zip
cd deploy-context-suite
docker compose build
docker compose up
```

Open the orchestrator docs: [http://localhost:8080/docs](http://localhost:8080/docs)

### Example request

```bash
curl -X POST http://localhost:8080/analyze \
  -F 'instruction=deploy to AWS with containers and a Postgres DB' \
  -F 'repo_zip=@/path/to/your/repo.zip'
```

You’ll get rich JSON like:

* `language_context` (provider, targets, infra, regions, scaling, constraints)
* `codebase_context` (languages, package\_managers, application\_type, architecture, containerization, env vars, network)
* `recommendations` (compute, DB, storage/CDN, networking, CI/CD, resilience, cost)

If you want me to tailor the heuristics (e.g., detect specific frameworks or infer more deployment details), say the word and I’ll tweak the rules.

---

Manual intervention to update test script


---

Prompt 2 (free GPT 5)

```
add deployment-suggestion service 3 that takes output of language context and codebase context and generate a suggestion sentence for deployment. 

account for single docker container, multi-microservice with many Dockerfile + docker-compose, and Kubernetes via minikube

service 4 "containerize-project" use service 3 output and input zip folder and apply suggestions

output of service 4 is a zip file artifact

use huggingface model and transformer pipeline if needed
```

Output of prompt 2:

Done — I added two new services and updated the project:

* **deployment-suggestion** (service 3) — `/suggest` (POST)
  Accepts `language_context` + `codebase_context` JSON and returns a concise suggestion plus structured type: `single-container`, `multi-microservice`, or `kubernetes-minikube`. It will optionally use a Hugging Face `transformers` pipeline if a model is available in the container.

* **containerize-project** (service 4) — `/apply` (POST)
  Accepts `suggestion_text` (optional), `suggestion_type` (optional), and `repo_zip` (required). Generates an artifact ZIP containing Dockerfiles, docker-compose, or Kubernetes manifests for minikube depending on the suggestion. The generated artifact is saved into `/mnt/data` and the API returns its path.

I updated:

* `docker-compose.yml` to include the two new services.
* `README.md` with a description and a sample `test.sh`.
* `test.sh` in the project root (executable) with the sequence: call orchestrator → call suggestion → call containerize-project.

Download the updated project ZIP here:
[sandbox:/mnt/data/deploy-context-suite-updated.zip](sandbox:/mnt/data/deploy-context-suite-updated.zip)

How would you like me to proceed next?

* Run a demo with a sample `hello_world.zip` and show the exact `result.json` and artifact?
* Tweak the suggestion text style (short one-liner vs. detailed paragraphs)?

---

Prompt 3 (GPT 4o): update orchestrator source code

Prompt 3 response: 

Got it! We’ll update the **orchestrator** so that it fully handles all internal service calls. The user only interacts with **one endpoint**, `/analyze`, which:

1. Sends the instruction to **language-context**.
2. Sends the repo ZIP to **codebase-context**.
3. Sends both results to **deployment-suggestion**.
4. Optionally calls **containerize-project** to produce the artifact ZIP.
5. Returns a **single aggregated JSON** including: `language_context`, `codebase_context`, `deployment_suggestion`, and optionally `artifact_zip`.

Here’s a full updated `orchestrator/app.py`:

```python
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
```

### ✅ Key Features

* **Single API endpoint:** `/analyze`.
* Internal services communicate **only via Docker network**.
* Supports optional artifact generation (`generate_artifact=True`).
* Returns a single aggregated JSON with all context + suggestion + artifact path.

---

If you want, I can also **update `docker-compose.yml`** and **`test.sh`** to match this new single-entrypoint orchestrator flow so users never need to call other services manually.

Do you want me to do that next?
---