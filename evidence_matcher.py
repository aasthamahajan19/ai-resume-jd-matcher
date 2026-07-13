import json
import re
from gemini_helper import call_gemini


EVIDENCE_CHECK_PROMPT = """You are evaluating whether a resume provides evidence for a specific job requirement.

Requirement:
{requirement}

Relevant resume excerpts:
{resume_excerpts}

Evaluate strictly:

- "strong": Resume shows clear, specific, demonstrated experience matching this requirement, such as a concrete project, measurable outcome, or named tools and techniques used in context.

- "weak": Resume mentions the topic or tool but without clear demonstrated depth, such as a keyword listing or vague claim.

- "missing": No evidence exists, even indirectly.

Rules:
1. Do not count keyword presence alone as strong evidence.
2. A skill listed without project or work context is weak at best.
3. Use only the provided resume excerpts.
4. Do not invent evidence.
5. If verdict is "missing", evidence_quote must be an empty string.
6. Keep reasoning to one short sentence.

Return ONLY one valid JSON object.

Required format:
{{"verdict":"strong","evidence_quote":"exact resume text","reasoning":"one short sentence"}}

Allowed verdict values:
- "strong"
- "weak"
- "missing"

Do not add markdown.
Do not add code fences.
Do not add explanation outside the JSON object.
Ensure all strings are properly escaped.
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
        "verdict",
        "evidence_quote",
        "reasoning"
    }

    if not required_keys.issubset(result.keys()):
        return False

    if result["verdict"] not in {
        "strong",
        "weak",
        "missing"
    }:
        return False

    return True


BATCH_EVIDENCE_PROMPT = """You are evaluating whether a resume provides evidence for a list of job requirements.

For EACH requirement below, evaluate strictly using only its own listed resume excerpts:

- "strong": Resume shows clear, specific, demonstrated experience matching the requirement, such as a concrete project, measurable outcome, or named tools and techniques used in context.

- "weak": Resume mentions the topic or tool but without clear demonstrated depth, such as a keyword listing or vague claim.

- "missing": No evidence exists, even indirectly.

Rules:
1. Do not count keyword presence alone as strong evidence.
2. A skill listed without project or work context is weak at best.
3. Use only the resume excerpts listed under that specific requirement.
4. Do not invent evidence.
5. If verdict is "missing", evidence_quote must be an empty string.
6. Keep reasoning to one short sentence per requirement.
7. Evaluate every requirement independently of the others.

Requirements:
{items_block}

Return ONLY a valid JSON array with exactly {count} objects, in the same order as the requirements above.

Required format for each object:
{{"index":1,"verdict":"strong","evidence_quote":"exact resume text","reasoning":"one short sentence"}}

Allowed verdict values:
- "strong"
- "weak"
- "missing"

Do not add markdown.
Do not add code fences.
Do not add explanation outside the JSON array.
Ensure all strings are properly escaped.
"""


def clean_json_array_response(text):
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


def validate_batch_item(item):
    if not isinstance(item, dict):
        return False

    required_keys = {
        "verdict",
        "evidence_quote",
        "reasoning"
    }

    if not required_keys.issubset(item.keys()):
        return False

    if item["verdict"] not in {
        "strong",
        "weak",
        "missing"
    }:
        return False

    return True


def _missing_result(reasoning):
    return {
        "verdict": "missing",
        "evidence_quote": "",
        "reasoning": reasoning
    }


def check_evidence_batch(api_key, batch_requirements, resume_units):
    """
    Evaluates a batch (list) of requirement strings against the
    resume in a single Gemini call. Returns a list of result dicts
    (verdict/evidence_quote/reasoning) in the same order as
    batch_requirements.
    """

    per_req_excerpts = []
    needs_call = []

    for requirement in batch_requirements:
        relevant_units = filter_relevant_units(
            requirement,
            resume_units
        )

        excerpts = "\n".join(
            f"  - {u.get('text', '')} "
            f"(from: {u.get('source', 'Unknown')})"
            for u in relevant_units
        )

        per_req_excerpts.append(excerpts.strip())
        needs_call.append(bool(excerpts.strip()))

    # If nothing has any excerpts, skip the API call entirely
    if not any(needs_call):
        return [
            _missing_result("No related content found in resume")
            for _ in batch_requirements
        ]

    items_block_parts = []

    for i, (requirement, excerpts) in enumerate(
        zip(batch_requirements, per_req_excerpts), start=1
    ):
        excerpt_text = excerpts if excerpts else "  (no related resume content found)"

        items_block_parts.append(
            f"{i}. Requirement: {requirement}\n"
            f"Resume excerpts:\n{excerpt_text}"
        )

    items_block = "\n\n".join(items_block_parts)

    prompt = BATCH_EVIDENCE_PROMPT.format(
        items_block=items_block,
        count=len(batch_requirements)
    )

    text = call_gemini(
        api_key,
        prompt,
        max_tokens=2000
    )

    text = clean_json_array_response(text)

    def parse_and_validate(candidate_text):
        parsed = json.loads(candidate_text)

        if not isinstance(parsed, list):
            raise ValueError("Gemini did not return a JSON array")

        if len(parsed) != len(batch_requirements):
            raise ValueError(
                f"Expected {len(batch_requirements)} results, "
                f"got {len(parsed)}"
            )

        for item in parsed:
            if not validate_batch_item(item):
                raise ValueError(
                    "Gemini returned an item with invalid structure"
                )

        # Sort by declared index if present, otherwise trust order
        try:
            parsed = sorted(
                parsed,
                key=lambda item: item.get("index", 0)
            )
        except TypeError:
            pass

        results = []

        for item in parsed:
            if item["verdict"] == "missing":
                item["evidence_quote"] = ""

            results.append(item)

        return results

    try:
        return parse_and_validate(text)

    except (json.JSONDecodeError, ValueError) as e:
        print("\n---- RAW GEMINI BATCH EVIDENCE OUTPUT ----")
        print(text)
        print("-------------------------------------------")
        print("ERROR:", e)

        repair_prompt = f"""
Fix the malformed or invalid JSON below.

Return ONLY a valid JSON array with exactly {len(batch_requirements)} objects.

Required keys per object:
- "index"
- "verdict"
- "evidence_quote"
- "reasoning"

Allowed verdict values:
- "strong"
- "weak"
- "missing"

Rules:
1. Do not add markdown.
2. Do not add code fences.
3. Do not add explanation.
4. Properly escape all strings.
5. If verdict is "missing", evidence_quote must be "".
6. Keep reasoning to one short sentence per object.

Malformed JSON:
{text}
"""

        repaired_text = call_gemini(
            api_key,
            repair_prompt,
            max_tokens=2000
        )

        repaired_text = clean_json_array_response(repaired_text)

        try:
            return parse_and_validate(repaired_text)

        except (json.JSONDecodeError, ValueError) as repair_error:
            print(
                "\n---- REPAIRED BATCH EVIDENCE OUTPUT INVALID ----"
            )
            print(repaired_text)
            print("--------------------------------------------------")
            print("REPAIR ERROR:", repair_error)

        return [
            _missing_result(
                "Evidence evaluation could not be completed reliably"
            )
            for _ in batch_requirements
        ]


def check_evidence(api_key, requirement, resume_units):
    relevant_units = filter_relevant_units(
        requirement,
        resume_units
    )

    excerpts = "\n".join(
        f"- {u.get('text', '')} "
        f"(from: {u.get('source', 'Unknown')})"
        for u in relevant_units
    )

    if not excerpts.strip():
        return {
            "verdict": "missing",
            "evidence_quote": "",
            "reasoning": "No related content found in resume"
        }

    prompt = EVIDENCE_CHECK_PROMPT.format(
        requirement=requirement,
        resume_excerpts=excerpts
    )

    text = call_gemini(
        api_key,
        prompt,
        max_tokens=1000
    )

    text = clean_json_response(text)

    try:
        result = json.loads(text)

        if validate_result(result):
            if result["verdict"] == "missing":
                result["evidence_quote"] = ""

            return result

        raise ValueError(
            "Gemini returned JSON with invalid structure"
        )

    except (json.JSONDecodeError, ValueError) as e:
        print("\n---- RAW GEMINI EVIDENCE OUTPUT ----")
        print(text)
        print("------------------------------------")
        print("ERROR:", e)

        repair_prompt = f"""
Fix the malformed or invalid JSON below.

Return ONLY one valid JSON object.

Required keys:
- "verdict"
- "evidence_quote"
- "reasoning"

Allowed verdict values:
- "strong"
- "weak"
- "missing"

Rules:
1. Do not add markdown.
2. Do not add code fences.
3. Do not add explanation.
4. Properly escape all strings.
5. If verdict is "missing", evidence_quote must be "".
6. Keep reasoning to one short sentence.

Malformed JSON:
{text}
"""

        repaired_text = call_gemini(
            api_key,
            repair_prompt,
            max_tokens=1000
        )

        repaired_text = clean_json_response(
            repaired_text
        )

        try:
            result = json.loads(repaired_text)

            if validate_result(result):
                if result["verdict"] == "missing":
                    result["evidence_quote"] = ""

                return result

        except json.JSONDecodeError as repair_error:
            print(
                "\n---- REPAIRED EVIDENCE OUTPUT INVALID ----"
            )
            print(repaired_text)
            print("------------------------------------------")
            print("REPAIR ERROR:", repair_error)

        return {
            "verdict": "missing",
            "evidence_quote": "",
            "reasoning": "Evidence evaluation could not be completed reliably"
        }


def check_all_evidence(api_key, requirements, resume_units, batch_size=8):
    """
    Evaluates all requirement dicts (each with at least a
    "requirement" key) against the parsed resume_units, batching
    multiple requirements into a single Gemini call (batch_size at
    a time) instead of one call per requirement. Returns a list of
    result dicts merging the original requirement fields with the
    verdict/evidence_quote/reasoning fields, in the original order.
    """

    results = []

    for start in range(0, len(requirements), batch_size):
        chunk = requirements[start:start + batch_size]

        chunk_texts = [
            req.get("requirement", "")
            for req in chunk
        ]

        try:
            chunk_verdicts = check_evidence_batch(
                api_key,
                chunk_texts,
                resume_units
            )

            if (
                not isinstance(chunk_verdicts, list)
                or len(chunk_verdicts) != len(chunk)
            ):
                raise ValueError(
                    "Batch evidence check returned mismatched results"
                )

        except Exception as e:
            print("\n---- BATCH EVIDENCE CHECK FAILED ----")
            print("Requirements:", chunk_texts)
            print("Error:", e)
            print("--------------------------------------")

            chunk_verdicts = [
                _missing_result("Evidence evaluation failed")
                for _ in chunk
            ]

        for req, verdict in zip(chunk, chunk_verdicts):

            if not isinstance(verdict, dict):
                verdict = _missing_result(
                    "Evidence checker returned an invalid response"
                )

            verdict_value = verdict.get("verdict", "missing")

            if verdict_value not in {"strong", "weak", "missing"}:
                verdict_value = "missing"

            evidence_quote = verdict.get("evidence_quote", "")
            reasoning = verdict.get("reasoning", "")

            if verdict_value == "missing":
                evidence_quote = ""

            results.append({
                **req,
                "verdict": verdict_value,
                "evidence_quote": str(evidence_quote or ""),
                "reasoning": str(reasoning or "")
            })

    return results


def normalize_words(text):
    return set(
        re.findall(
            r"\b[a-zA-Z0-9+#.]+\b",
            text.lower()
        )
    )


def filter_relevant_units(
    requirement,
    resume_units,
    top_k=8
):
    if not resume_units:
        return []

    req_words = normalize_words(requirement)

    scored = []

    for unit in resume_units:
        unit_text = unit.get("text", "")
        unit_words = normalize_words(unit_text)

        overlap = len(
            req_words & unit_words
        )

        scored.append(
            (overlap, unit)
        )

    scored.sort(
        key=lambda x: -x[0]
    )

    if len(resume_units) <= top_k:
        return resume_units

    positive_matches = [
        unit
        for score, unit in scored
        if score > 0
    ]

    if positive_matches:
        return positive_matches[:top_k]

    return []