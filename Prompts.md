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
