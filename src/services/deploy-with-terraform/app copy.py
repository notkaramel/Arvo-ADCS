import os
from flask import Flask, request, jsonify, render_template
import openai
import logging

app = Flask(__name__)

openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    # Use a more descriptive error message than a simple alert.
    print("Error: OPENAI_API_KEY environment variable not found.")
    # In a production app, you might raise an exception or handle this more gracefully.
    # For now, we'll just continue and the API call will fail.
    # You can also use python-dotenv for local development.
    pass

openai.api_key = openai_api_key


@app.route('/')
def index():
    return jsonify({"message": "Deployment Suggestion Service is running."})


@app.route('/suggest', methods=['POST'])
def generate_text():
    """Handles the API call to OpenAI."""

    data = request.json
    language_context = data.get('language_context')
    codebase_context = data.get('codebase_context')

    if not language_context or not codebase_context:
        return jsonify({'error': 'No prompt provided'}), 400

    prompt = f"JSON with keys 'language', 'type', 'architecture',\
        'is_containerized', 'env_variables', 'network_settings', \
        'cloud_provider', 'infrastructure', generate best deployment\
        strategy for the following programming language context:\
        {language_context} and codebase: {codebase_context}"

    # Call the OpenAI Chat API
    response = openai.OpenAI().responses.create(
        model="gpt-5",
        input=prompt,
        reasoning={"effort": "minimal"},
    )

    # Extract the generated text
    return response.output_text


if __name__ == '__main__':
    # Use 0.0.0.0 for public access in a production environment
    app.run(host='0.0.0.0', port=8080)
