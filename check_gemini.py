import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).parent / ".env")

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not api_key:
    raise SystemExit("GEMINI_API_KEY is missing from the project's .env file.")

client = genai.Client(api_key=api_key)
try:
    response = client.models.generate_content(
        model=model,
        contents="In one short sentence, explain why weather forecasts can change.",
        config=genai.types.GenerateContentConfig(max_output_tokens=80),
    )
except genai.errors.APIError as error:
    print(f"Gemini model: {model}")
    print(f"Gemini returned HTTP {error.code} ({error.status}): {error.message}")
    raise SystemExit(1) from error
finally:
    client.close()

if not response.text:
    feedback = response.prompt_feedback
    block_reason = (
        feedback.block_reason.name
        if feedback and feedback.block_reason
        else "none"
    )
    candidate_summaries = [
        (
            f"finish_reason={candidate.finish_reason.name if candidate.finish_reason else 'unknown'}, "
            f"finish_message={candidate.finish_message or 'none'}"
        )
        for candidate in response.candidates or []
    ]
    output_tokens = (
        response.usage_metadata.candidates_token_count
        if response.usage_metadata
        else None
    )
    raise SystemExit(
        f"Gemini model {model} returned no text. "
        f"Prompt block reason: {block_reason}. "
        f"Candidates: {candidate_summaries or 'none'}. "
        f"Output tokens: {output_tokens if output_tokens is not None else 'unknown'}."
    )

print(f"Gemini model: {model}")
print(f"Gemini reply: {response.text.strip()}")
