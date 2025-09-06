#!/usr/bin/env bash
set -e

# Call orchestrator (single entrypoint)
curl -X POST http://localhost:8080/analyze \
  -F 'instruction=deploy to AWS with containers and a Postgres DB' \
  -F 'repo_zip=@hello_world.zip' \
  -o result.json

echo "Aggregated results saved to result.json"
artifact=$(jq -r '.artifact_zip' result.json)
if [[ "$artifact" != "null" && "$artifact" != "" ]]; then
  echo "Artifact ZIP generated at: $artifact"
fi