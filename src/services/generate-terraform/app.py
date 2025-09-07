from flask import Flask, request, send_file, jsonify
import tempfile
import zipfile
import os
import io
import json
import datetime
import logging
import openai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB upload limit
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------
# OpenAI helper
# -------------------------------


def call_openai_for_infra(suggestion: dict):
    prompt = f"""Generate Terraform config files (`main.tf`, `provider.tf`,
    `variables.tf`, `outputs.tf`), docker-compose.yaml for local development,
    and terraform_config.json echoing the input JSON.

    ONLY valid file contents.

    Suggestion JSON:
    {json.dumps(suggestion, indent=2)}
    """

    response = openai.OpenAI().responses.create(
        model="gpt-5",
        input=prompt,
        reasoning={"effort": "minimal"},
    )
    return response.output_text


# -------------------------------
# Generate Terraform files
# -------------------------------
def generate_terraform_files(suggestion: dict, outdir: str):
    os.makedirs(outdir, exist_ok=True)
    content = call_openai_for_infra(suggestion)

    files = {
        "main.tf": "",
        "provider.tf": "",
        "variables.tf": "",
        "outputs.tf": "",
        "terraform_config.json": json.dumps(suggestion, indent=2),
    }

    current_file = None
    for line in content.splitlines():
        if line.strip().startswith("```") and current_file:
            current_file = None
            continue
        if line.strip().startswith("```"):
            continue

        if "main.tf" in line:
            current_file = "main.tf"
            continue
        if "provider.tf" in line:
            current_file = "provider.tf"
            continue
        if "variables.tf" in line:
            current_file = "variables.tf"
            continue
        if "outputs.tf" in line:
            current_file = "outputs.tf"
            continue

        if current_file:
            files[current_file] += line + "\n"

    for fname, text in files.items():
        fpath = os.path.join(outdir, fname)
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w") as f:
            f.write(text)

    # optional README
    with open(os.path.join(outdir, "README.md"), "w") as f:
        f.write(
            f"# Auto-generated Terraform files\nGenerated {datetime.datetime.utcnow().isoformat()}Z\n")

# -------------------------------
# Flask endpoint
# -------------------------------


@app.route("/terraform", methods=["POST"])
def generate_terraform():
    data = request.get_json()
    if not data or "suggestion" not in data:
        return jsonify({"error": "Missing 'suggestion' field"}), 400

    suggestion = data["suggestion"]

    with tempfile.TemporaryDirectory() as tmpdir:
        generate_terraform_files(suggestion, tmpdir)

        # create ZIP in memory
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, "w") as zipf:
            for root, _, files in os.walk(tmpdir):
                for f in files:
                    full_path = os.path.join(root, f)
                    arcname = os.path.relpath(full_path, tmpdir)
                    zipf.write(full_path, arcname)
        zip_stream.seek(0)

        return send_file(
            zip_stream,
            mimetype="application/zip",
            as_attachment=True,
            download_name="terraformed.zip",
        )


@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Terraform Generation Service is running."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
