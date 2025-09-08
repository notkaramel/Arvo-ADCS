#!/usr/bin/env bash
set -e

curl -X POST http://localhost:8080/upload \
  -F 'instruction=Deploy my project to Google Cloud' \
  -F 'repo_zip=@hello_world.zip' \
  -o result.json

cat result.json