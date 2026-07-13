import json
import re
from gemini_helper import call_gemini

REQUIREMENT_EXTRACTION_PROMPT = """You are analyzing a job description to extract discrete, checkable requirements.

Job Description:
{jd_text}

Extract every requirement mentioned, including:
- skills
- years of experience
- tools
- domains
- soft skills
- education

For each requirement, classify category as:
- "required" for must-have requirements
- "preferred" for nice-to-have, preferred, plus, or bonus requirements

Classify type as one of:
- "hard_skill"
- "soft_skill"
- "experience"
- "education"
- "domain"

Return ONLY a valid JSON array.

Rules:
1. No markdown.
2. No code fences.
3. No explanation.
4. Every object must contain:
   - "requirement"
   - "category"
   - "type"
5. Keep each requirement under 150 characters.
6. Replace double quotes inside values with single quotes.
7. Do not include line breaks inside string values.
8. Properly escape all JSON strings.
9. Ensure the complete JSON array is closed.

Example:
[
  {{"requirement":"5+ years of Python development","category":"required","type":"experience"}},
  {{"requirement":"Experience with distributed systems","category":"required","type":"hard_skill"}},
  {{"requirement":"Strong communication skills","category":"required","type":"soft_skill"}},
  {{"requirement":"Experience with Kubernetes","category":"preferred","type":"hard_skill"}}
]
"""


def clean_json_response(text):
    text = text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace("```", "").strip()

    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end != -1:
        text = text[start:end + 1]

    return text


def extract_requirements(api_key, jd_text):
    prompt = REQUIREMENT_EXTRACTION_PROMPT.format(
        jd_text=jd_text
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

        repair_prompt = f"""
Fix the malformed JSON below.

Return ONLY the corrected valid JSON array.
Do not add markdown.
Do not add code fences.
Do not add explanation.
Do not remove useful requirements.

Every object must contain:
- "requirement"
- "category"
- "type"

Allowed category values:
- "required"
- "preferred"

Allowed type values:
- "hard_skill"
- "soft_skill"
- "experience"
- "education"
- "domain"

Ensure:
- all strings are properly escaped
- no string contains unescaped double quotes
- the complete JSON array is closed

Malformed JSON:
{text}
"""

        repaired_text = call_gemini(
            api_key,
            repair_prompt,
            max_tokens=8000
        )

        repaired_text = clean_json_response(
            repaired_text
        )

        try:
            return json.loads(repaired_text)

        except json.JSONDecodeError as repair_error:
            print(
                "\n---- REPAIRED OUTPUT ALSO INVALID ----"
            )
            print(repaired_text)
            print("--------------------------------------")
            print("REPAIR ERROR:", repair_error)

            return []