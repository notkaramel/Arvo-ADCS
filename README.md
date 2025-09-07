# Design phase

- First attempt: https://excalidraw.com/#json=jxKZ8GsbIm_8_ZP-0-nGZ,IblhtM3I1DW1aoGsxCA71Q
  ![System design stages](docs/SystemDesign1.png)
  ![Microservices Architecture](docs/Architecture1.png)

# Implementation phase

- Orchestrator
- Microservices, in order of stages
  | Microservice | Order | Input | Output |
  | ------------------------- | ----- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
  | **language-context** | 1 | `instruction` string | JSON: `cloud_provider`, `infrastructure`, etc. |
  | **codebase-context** | 2 | `repo_zip` | JSON: language, package manager, app type, architecture, containerized, env, network |
  | **deployment-suggestion** | 3 | language + codebase context | JSON: `suggestion_text`, `type` (`single-docker`, `multi-docker`, `kubernetes-minikube`) |
  | **containerize-project** | 4 | `repo_zip`, `suggestion` | ZIP: Dockerfiles, docker-compose, manifests |
  | **containerization** | 5 | `repo_zip`, `deployment_suggestion` | Skip if project already containerized; otherwise generates Dockerfile/docker-compose ZIP |
  | **generate-terraform** | 6 | language + codebase context, environment variables | Terraform config files for GCP or Azure (zip or folder) |
  | **deploy-with-terraform** | 7 | Terraform config + containerized project | Starts deployment, exposes internal API to monitor/supervise, returns deployment status + endpoints |

## Quick start

```bash
docker compose build
docker compose up
```
