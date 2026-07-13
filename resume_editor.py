import json
import re
from gemini_helper import call_gemini


RESUME_EDIT_PROMPT = """You are an expert ATS resume editor.

Your task is to tailor the candidate's resume to the given job description.

JOB DESCRIPTION:
{jd_text}

ORIGINAL RESUME:
{resume_text}

STRICT RULES:
1. Do not invent skills, projects, jobs, education, certifications, metrics, or experience.
2. Use only facts already present in the original resume.
3. Improve wording to align with the job description.
4. Naturally emphasize relevant existing skills and experience.
5. Use strong action verbs.
6. Improve ATS keyword alignment only when supported by the resume.
7. Do not claim missing requirements as existing experience.
8. Keep measurable achievements if already present.
9. Preserve names, dates, companies, colleges, degrees, and project facts.
10. Keep the resume professional and concise.
11. Return complete tailored resume content.
12. Mention unsupported important JD requirements separately as suggestions.

Return ONLY valid JSON in this exact structure:

{{
  "tailored_resume": "Complete rewritten resume text",
  "changes_made": [
    "Description of change 1",
    "Description of change 2"
  ],
  "missing_keywords": [
    "Important JD requirement not supported by resume"
  ]
}}

No markdown.
No code fences.
No explanation outside JSON.
Properly escape all JSON strings.
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

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start:end + 1]

    return text


def validate_result(result):
    if not isinstance(result, dict):
        return False

    required_keys = {
        "tailored_resume",
        "changes_made",
        "missing_keywords"
    }

    if not required_keys.issubset(result.keys()):
        return False

    if not isinstance(result["tailored_resume"], str):
        return False

    if not isinstance(result["changes_made"], list):
        return False

    if not isinstance(result["missing_keywords"], list):
        return False

    return True


def tailor_resume(api_key, jd_text, resume_text):
    prompt = RESUME_EDIT_PROMPT.format(
        jd_text=jd_text,
        resume_text=resume_text
    )

    text = call_gemini(
        api_key,
        prompt,
        max_tokens=8000,
        temperature=0.2
    )

    text = clean_json_response(text)

    try:
        result = json.loads(text)

        if validate_result(result):
            return result

        raise ValueError(
            "Gemini returned invalid response structure"
        )

    except (json.JSONDecodeError, ValueError) as e:
        print("\n---- RESUME EDIT OUTPUT INVALID ----")
        print(text)
        print("------------------------------------")
        print("ERROR:", e)

        repair_prompt = f"""
Fix the JSON below.

Return ONLY one valid JSON object.

Required structure:
{{
  "tailored_resume": "Complete rewritten resume text",
  "changes_made": [],
  "missing_keywords": []
}}

Rules:
- Do not add markdown
- Do not add code fences
- Properly escape strings
- Preserve the existing content
- Do not invent candidate experience

Invalid JSON:
{text}
"""

        repaired_text = call_gemini(
            api_key,
            repair_prompt,
            max_tokens=8000,
            temperature=0.1
        )

        repaired_text = clean_json_response(
            repaired_text
        )

        try:
            result = json.loads(repaired_text)

            if validate_result(result):
                return result

        except json.JSONDecodeError as repair_error:
            print(
                "\n---- REPAIRED RESUME OUTPUT INVALID ----"
            )
            print(repaired_text)
            print("----------------------------------------")
            print("ERROR:", repair_error)

        return {
            "tailored_resume": resume_text,
            "changes_made": [],
            "missing_keywords": [],
            "error": "Could not safely tailor resume"
        }