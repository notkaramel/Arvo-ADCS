from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Context(BaseModel):
    language_context: dict
    codebase_context: dict

@app.post("/")
async def suggest(ctx: Context):
    # prompt = f"Generate deployment suggestion based on context: {ctx.json()}"
    output = [{"generated_text": "Use a single Docker container with Python 3.12 and necessary dependencies."}]
    suggestion_text = output[0]["generated_text"]
    suggestion_type = "single-docker"  # simple logic for now

    return {
        "suggestion": {
            "suggestion_text": suggestion_text,
            "type": suggestion_type
        }
    }
