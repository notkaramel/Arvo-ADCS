# Arvo-ADCS

- An automated deployment chat-ish system. Backend-focus
- Designed (entirely) by @notkaramel, implemented with the help of ChatGPT 5 and Gemini 2.5 Flash.

## Design phase

- Updated attempt:

  - Full system sketch: https://excalidraw.com/#json=3T5yRD1cPPOXs3K85h0fV,7p1pSMCrBKGi2ZZ-5tcmVg
  - ![Microservices Architecture](docs/Architecture2.png)

- First attempt:

  - Full system sketch https://excalidraw.com/#json=jxKZ8GsbIm_8_ZP-0-nGZ,IblhtM3I1DW1aoGsxCA71Q
  - ![System design stages](docs/SystemDesign1.png)

  - ![Microservices Architecture](docs/Architecture1.png)

## Implementation phase

- Orchestrator
- Microservices, in order of stages
  | Microservice | Order | Input | Output |
  | ------------------------- | ----- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
  | **language-context** | 1 | `instruction` string | JSON: `cloud_provider`, `infrastructure`, etc. |
  | **codebase-context** | 2 | `repo_zip` | JSON: language, package manager, app type, architecture, containerized, env, network |
  | **deployment-suggestion** | 3 | language + codebase context | JSON: `suggestion_text`, `type` (`single-docker`, `multi-docker`, `kubernetes-minikube`) |
  | **containerize-project** | 4 | `repo_zip`, `suggestion` | Skip if project already containerized; otherwise generates Dockerfile/docker-compose ZIP |
  | **generate-terraform** | 6 | language + codebase context, environment variables | Terraform config files for GCP or Azure (zip or folder) |
  | **deploy-with-terraform** | 7 | Terraform config + containerized project | Starts deployment, exposes internal API to monitor/supervise, returns deployment status + endpoints |

## API

- Input to Orchestrator: http://orchestrator:8080/upload or http://localhost:8080/upload
- Request body requires:
  - Deployment Instruction `instruction`, string
  - ZIP file of the project

## Quick start

```bash
docker compose build
docker compose up -d
```

The frontend is available at localhost:80

## Sample Output

After "Generate Terraform" stage, users should be able to retrieve a zip file containing their original project + Terraform configured files. Here's the sample output from "Deploy my project to Google Cloud" with the _`hello_world.zip`_ project

```
[antoine@LunarEclipse:~/Partage/Projects/Arvo-ADCS on main]
% tree terraform_generated
terraform_generated
├── hello_world_webserver-main
│   ├── app
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   ├── static
│   │   │   └── style.css
│   │   └── templates
│   │       └── index.html
│   └── README.md
├── main.tf
├── outputs.tf
├── provider.tf
├── README.md
├── terraform_config.json
└── variables.tf

5 directories, 11 files
```
