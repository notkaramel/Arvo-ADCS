from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
import tempfile, zipfile, os, shutil, json, io, datetime
import openai

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB upload limit

openai.api_key = os.getenv("OPENAI_API_KEY")  # set your API key in env

# -------------------------------
# Helper: call OpenAI to generate infra files
# -------------------------------
def call_openai_for_infra(suggestion: dict):
    prompt = f"""Generate Terraform config files (`main.tf`, `provider.tf`,
    `variables.tf`, `outputs.tf`), docker-compose.yaml for local development
    terraform_config.json echoing the input JSON

    ONLY valid file content.

    Suggestion JSON:
    {json.dumps(suggestion, indent=2)}
    """

    # Call the OpenAI Chat API
    response = openai.OpenAI().responses.create(
        model="gpt-5",
        input=prompt,
        reasoning={"effort": "minimal"},
    )

    # Extract the generated text
    return response.output_text


# -------------------------------
# File generation
# -------------------------------
def generate_infra_with_openai(suggestion: dict, outdir: str):
    os.makedirs(outdir, exist_ok=True)

    # call model
    content = call_openai_for_infra(suggestion)

    # crude parsing: split blocks by file hints
    files = {
        "terraform/main.tf": "",
        "terraform/provider.tf": "",
        "terraform/variables.tf": "",
        "terraform/outputs.tf": "",
        "docker-compose.yaml": "",
        "config/terraform_config.json": json.dumps(suggestion, indent=2),
    }

    current_file = None
    for line in content.splitlines():
        if line.strip().startswith("```") and current_file:
            current_file = None
            continue
        if line.strip().startswith("```"):
            continue

        # detect headers like main.tf
        if "main.tf" in line:
            current_file = "terraform/main.tf"
            continue
        if "provider.tf" in line:
            current_file = "terraform/provider.tf"
            continue
        if "variables.tf" in line:
            current_file = "terraform/variables.tf"
            continue
        if "outputs.tf" in line:
            current_file = "terraform/outputs.tf"
            continue
        if "docker-compose" in line:
            current_file = "docker-compose.yaml"
            continue

        if current_file:
            files[current_file] += line + "\n"

    # write files to disk
    for path, content in files.items():
        file_path = os.path.join(outdir, path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)

    # also add README
    with open(os.path.join(outdir, "README.md"), "w") as f:
        f.write(f"# Auto-generated infra files\nGenerated {datetime.datetime.utcnow().isoformat()}Z\n")


# -------------------------------
# Flask endpoint
# -------------------------------
@app.route('/generate', methods=['POST'])
def generate():
    if 'code_zip' not in request.files:
        return jsonify({"error": "Missing file field 'code_zip'"}), 400

    code_zip = request.files['code_zip']
    if code_zip.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    suggestion = None
    if 'suggestion' in request.files:
        suggestion = json.load(request.files['suggestion'])
    elif 'suggestion' in request.form:
        suggestion = json.loads(request.form['suggestion'])
    else:
        return jsonify({"error": "Missing suggestion JSON"}), 400

    filename = secure_filename(code_zip.filename)
    with tempfile.TemporaryDirectory() as tmpdir:
        upload_path = os.path.join(tmpdir, filename)
        code_zip.save(upload_path)

        extract_dir = os.path.join(tmpdir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(upload_path, 'r') as z:
            z.extractall(extract_dir)

        # generate infra files
        generate_infra_with_openai(suggestion, extract_dir)

        # repackage
        out_zip_name = f"{os.path.splitext(filename)[0]}-with-infra.zip"
        out_zip_path = os.path.join(tmpdir, out_zip_name)
        shutil.make_archive(os.path.splitext(out_zip_path)[0], 'zip', extract_dir)

        return send_file(out_zip_path, mimetype="application/zip",
                         as_attachment=True, download_name=out_zip_name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
