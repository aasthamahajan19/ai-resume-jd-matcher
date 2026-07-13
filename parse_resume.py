import json
import re
from gemini_helper import call_gemini

RESUME_PARSE_PROMPT = """Parse this resume into discrete experience units.

Each unit should be one bullet point, one project, one role responsibility,
or one skill claim — something specific enough to check for evidence.

Resume:
{resume_text}

Return ONLY a valid JSON array.

Rules:
1. No markdown.
2. No code fences.
3. No explanation.
4. Every object must contain:
   - "unit_id"
   - "text"
   - "source"
5. Keep each text field under 150 characters.
6. Replace double quotes inside values with single quotes.
7. Do not include newline characters inside string values.
8. Ensure the JSON array is fully closed.

Example:
[
  {{"unit_id":"1","text":"Built a Python API for data processing","source":"Project"}},
  {{"unit_id":"2","text":"Used SQL for database management","source":"Skills"}}
]
"""


def clean_json_response(text):
    text = text.strip()

    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")
    text = text.strip()

    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end != -1:
        text = text[start:end + 1]

    return text


def parse_resume(api_key, resume_text):
    prompt = RESUME_PARSE_PROMPT.format(
        resume_text=resume_text
    )

    text = call_gemini(
        api_key,
        prompt,
        max_tokens=8000
    )

    text = clean_json_response(text)

    try:
        return json.loads(text)

    except json.JSONDecodeError as e:
        print("\n---- RAW GEMINI OUTPUT ----")
        print(text)
        print("---------------------------")
        print("JSON ERROR:", e)

        # Ask Gemini to repair its own malformed JSON
        repair_prompt = f"""
Fix the malformed JSON below.

Return ONLY the corrected valid JSON array.
Do not add markdown.
Do not add explanation.
Do not remove useful data.
Ensure all strings are properly escaped.

Malformed JSON:
{text}
"""

        repaired_text = call_gemini(
            api_key,
            repair_prompt,
            max_tokens=8000
        )

        repaired_text = clean_json_response(repaired_text)

        try:
            return json.loads(repaired_text)

        except json.JSONDecodeError as repair_error:
            print("\n---- REPAIRED OUTPUT ALSO INVALID ----")
            print(repaired_text)
            print("--------------------------------------")
            print("REPAIR ERROR:", repair_error)

            return []