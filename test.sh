#!/usr/bin/env bash
set -e

curl -X POST http://localhost:8080/ \
  -F 'instruction=deploy to AWS with containers and a Postgres DB' \
  -F 'repo_zip=@hello_world.zip' \
  -o result.json

cat result.json