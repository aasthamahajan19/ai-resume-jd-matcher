from extract_requirements import extract_requirements
from parse_resume import parse_resume
from evidence_matcher import check_all_evidence


def analyze_resume_against_jd(api_key, jd_text, resume_text):
    if not jd_text or not jd_text.strip():
        return {
            "overall_score": 0,
            "requirements": [],
            "summary": {
                "strong": 0,
                "weak": 0,
                "missing": 0
            },
            "error": "Job description is empty"
        }

    if not resume_text or not resume_text.strip():
        return {
            "overall_score": 0,
            "requirements": [],
            "summary": {
                "strong": 0,
                "weak": 0,
                "missing": 0
            },
            "error": "Resume text is empty"
        }

    try:
        requirements = extract_requirements(api_key, jd_text)
    except Exception as e:
        print("\n---- REQUIREMENT EXTRACTION FAILED ----")
        print(e)
        print("---------------------------------------")
        requirements = []

    try:
        resume_units = parse_resume(api_key, resume_text)
    except Exception as e:
        print("\n---- RESUME PARSING FAILED ----")
        print(e)
        print("--------------------------------")
        resume_units = []

    if not isinstance(requirements, list):
        requirements = []

    if not isinstance(resume_units, list):
        resume_units = []

    valid_requirements = []

    for req in requirements:
        if not isinstance(req, dict):
            continue

        requirement = req.get(
            "requirement",
            ""
        )

        if not requirement or not str(requirement).strip():
            continue

        category = req.get(
            "category",
            "required"
        )

        if category not in {
            "required",
            "preferred"
        }:
            category = "required"

        req_type = req.get(
            "type",
            "hard_skill"
        )

        valid_requirements.append({
            "requirement": str(requirement).strip(),
            "category": category,
            "type": req_type
        })

    requirements = valid_requirements

    results = check_all_evidence(
        api_key,
        requirements,
        resume_units
    )

    def points(result):
        verdict_scores = {
            "strong": 1.0,
            "weak": 0.4,
            "missing": 0.0
        }

        base = verdict_scores.get(
            result.get("verdict"),
            0.0
        )

        category = result.get(
            "category",
            "required"
        )

        weight = (
            1.5
            if category == "required"
            else 1.0
        )

        return base * weight

    total_possible = sum(
        1.5
        if req.get("category") == "required"
        else 1.0
        for req in requirements
    )

    total_earned = sum(
        points(result)
        for result in results
    )

    score = (
        round(
            (total_earned / total_possible) * 100,
            1
        )
        if total_possible > 0
        else 0
    )

    score = max(
        0,
        min(100, score)
    )

    return {
        "overall_score": score,
        "requirements": results,
        "summary": {
            "strong": sum(
                1
                for result in results
                if result["verdict"] == "strong"
            ),
            "weak": sum(
                1
                for result in results
                if result["verdict"] == "weak"
            ),
            "missing": sum(
                1
                for result in results
                if result["verdict"] == "missing"
            )
        }
    }