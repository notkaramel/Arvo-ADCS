# Design phase
- First attempt: https://excalidraw.com/#json=jxKZ8GsbIm_8_ZP-0-nGZ,IblhtM3I1DW1aoGsxCA71Q
![System design stages](docs/SystemDesign1.png)
![Microservices Architecture](docs/Architecture1.png)


# Implementation phase
- Orchestrator
- Microservices, in order of stages
    - 

--- 
> ChatGPT generated README

# Deploy Context Suite

Three FastAPI microservices with Docker + docker-compose:

- **language-context**: Extracts deployment intent from a natural-language instruction (e.g., "deploy to AWS").
- **codebase-context**: Extracts signals from a repo ZIP (or folder) to understand languages, package managers, app type, architecture, env vars, containerization, and network settings.
- **orchestrator**: Accepts inputs and calls the two services, then returns merged JSON plus deployment suggestions.

## Quick start

```bash
docker compose build
docker compose up
```

Orchestrator API will be available at: `http://localhost:8080/docs`

### Orchestrator: POST /analyze

- Multipart form for file uploads:
  - `instruction` (text, required)
  - `repo_zip` (file, optional) — a ZIP of your repository
  - `repo_url` (text, optional) — recorded in output (no cloning by default)

**Example (cURL)**

```bash
curl -X POST http://localhost:8080/analyze   -F 'instruction=deploy to AWS with containers and a Postgres DB'   -F 'repo_zip=@/path/to/your/repo.zip'
```

### Outputs

Structured JSON with keys:

- `language_context` — extraction from instruction
- `codebase_context` — extraction from provided ZIP (if any)
- `recommendations` — suggested deployment paths (e.g., AWS ECS/EKS, RDS, S3+CloudFront, etc.)

## Notes

- The `codebase-context` service analyzes a provided ZIP; if you supply only `repo_url`, it will be included in the report but the code won’t be analyzed unless you extend the service to `git clone`.
- Add more rules in the Python modules under each service to improve detection over time.
