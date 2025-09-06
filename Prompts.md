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