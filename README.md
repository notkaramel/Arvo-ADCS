# Design phase

- First attempt: https://excalidraw.com/#json=jxKZ8GsbIm_8_ZP-0-nGZ,IblhtM3I1DW1aoGsxCA71Q
  ![System design stages](docs/SystemDesign1.png)
  ![Microservices Architecture](docs/Architecture1.png)

# Implementation phase

- Orchestrator
- Microservices, in order of stages
  | Microservice | Order | Input | Output |
  | ------------------------- | ----- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | **language-context** | 1.1 | `instruction` (string) e.g., _"deploy to AWS with containers and a Postgres DB"_ | JSON with extracted context: `cloud_provider`, `infrastructure`, `deployment_targets`, and raw instruction |
  | **codebase-context** | 1.2 | `repo_zip` (uploaded ZIP of project or GitHub repo) | JSON with `languages`, `package_manager`, `application_type`, `architecture`, `containerization` status, env variables, etc. |
  | **deployment-suggestion** | 3 | JSON with `language_context` + `codebase_context` | JSON with structured `suggestion` including `type` (`single-container`, `multi-microservice`, or `kubernetes-minikube`), detailed `sentences`, and optional HuggingFace-refined `suggestion_text` |
  | **containerize-project** | 4 | `suggestion_text`, `suggestion_type`, and `repo_zip` | ZIP artifact containing generated deployment setup (`Dockerfile`, `docker-compose.yml`, or `k8s/` manifests) |

## Quick start

```bash
docker compose build
docker compose up
```