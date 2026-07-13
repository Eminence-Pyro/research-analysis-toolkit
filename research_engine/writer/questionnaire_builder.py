"""
research_engine/writer/questionnaire_builder.py
Tier 1 #3 — Questionnaire auto-builder from objectives

Given a ProjectSession (with objectives, level, research design),
generates a complete questionnaire.json and demographics.json ready
for the dataset generation pipeline.

Public API
----------
    build_questionnaire(session, api_key, model)  → dict  (questionnaire.json content)
    build_demographics(session, api_key, model)   → dict  (demographics.json content)
    save_study_files(session, project_root)       → dict[str, Path]
"""
from __future__ import annotations

import json
import os
from pathlib import Path


# ══════════════════════════════════════════════════════════════
# Questionnaire builder
# ══════════════════════════════════════════════════════════════

def build_questionnaire(
    session,
    api_key: str | None = None,
    model:   str        = "gpt-4o",
) -> dict:
    """
    Build a questionnaire.json dict from the session's objectives and metadata.

    Returns a dict matching schemas/questionnaire.schema.json:
    {
      "title": "...",
      "scale": {"1": "Strongly Disagree", ..., "5": "Strongly Agree"},
      "sections": {
        "A": {"title": "...", "items": ["Question 1", ...]},
        ...
      }
    }
    """
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    m   = session.metadata

    objectives_text = "\n".join(
        f"{i+1}. {o}" for i, o in enumerate(m.objectives)
    ) if m.objectives else "Not specified — use general satisfaction/quality assessment items"

    rqs_text = "\n".join(
        f"{i+1}. {q}" for i, q in enumerate(m.research_questions)
    ) if m.research_questions else ""

    prompt = f"""You are a research instrument designer. Create a structured questionnaire
for the following study. Return ONLY valid JSON matching the exact format shown.

STUDY TITLE: {m.title or "Research Study"}
LEVEL: {m.level.value.upper()}
RESEARCH DESIGN: {m.research_design.value.replace("_"," ")}
OBJECTIVES:
{objectives_text}
{"RESEARCH QUESTIONS:" + chr(10) + rqs_text if rqs_text else ""}

INSTRUCTIONS:
- Create one questionnaire SECTION per objective (Section A, B, C, ...)
- Each section should have 4–6 Likert-scale items directly measuring that objective
- Use a 5-point Likert scale
- Item wording should be clear, specific, and appropriate for the study population
- Do NOT include demographic items (those go in a separate section)
- Section titles should be concise (4–6 words)

Return EXACTLY this JSON structure:
{{
  "title": "QUESTIONNAIRE TITLE",
  "study_title": "FULL STUDY TITLE",
  "version": "1.0",
  "scale": {{
    "1": "Strongly Disagree",
    "2": "Disagree",
    "3": "Neutral",
    "4": "Agree",
    "5": "Strongly Agree"
  }},
  "sections": {{
    "A": {{
      "title": "Section A Title",
      "items": ["Item 1 text", "Item 2 text", "Item 3 text", "Item 4 text", "Item 5 text"]
    }},
    "B": {{
      "title": "Section B Title",
      "items": ["Item 1 text", "Item 2 text", "Item 3 text", "Item 4 text"]
    }}
  }}
}}"""

    if not key:
        return _default_questionnaire(m)

    try:
        from openai import OpenAI
        client   = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        if "sections" in data and "scale" in data:
            return data
        return _default_questionnaire(m)
    except Exception:
        return _default_questionnaire(m)


def _default_questionnaire(m) -> dict:
    """Fallback questionnaire when LLM is unavailable."""
    sections = {}
    labels = "ABCDE"
    objectives = m.objectives or [
        "Quality of service delivery",
        "Staff attitude and responsiveness",
        "Physical environment and facilities",
    ]
    for i, obj in enumerate(objectives[:5]):
        key = labels[i]
        sections[key] = {
            "title": obj[:40],
            "items": [
                f"The {obj.lower()} meets my expectations.",
                f"I am satisfied with the {obj.lower()}.",
                f"The {obj.lower()} is consistently reliable.",
                f"I would recommend this service to others based on {obj.lower()}.",
            ]
        }
    return {
        "title": f"Questionnaire on {m.title or 'Research Study'}",
        "study_title": m.title or "",
        "version": "1.0",
        "scale": {"1":"Strongly Disagree","2":"Disagree","3":"Neutral",
                  "4":"Agree","5":"Strongly Agree"},
        "sections": sections,
    }


# ══════════════════════════════════════════════════════════════
# Demographics builder
# ══════════════════════════════════════════════════════════════

def build_demographics(
    session,
    api_key: str | None = None,
    model:   str        = "gpt-4o-mini",
) -> dict:
    """
    Build a demographics.json dict appropriate for the study's population.

    Returns a dict matching schemas/demographics.schema.json format:
    {
      "age": {"distribution": "normal", "mean": 28, "std": 7, "min": 18, "max": 65},
      "gender": {"Female": 0.72, "Male": 0.28},
      ...
    }
    """
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    m   = session.metadata

    prompt = f"""You are a research methods expert. Generate a demographics.json config
for a study with the following population profile.

STUDY: {m.title or "Research Study"}
POPULATION: {m.population or "General adult population"}
STUDY AREA: {m.study_area or "Nigeria"}
LEVEL: {m.level.value.upper()}

Generate realistic demographic distributions for this population.
Return ONLY valid JSON in exactly this format (use realistic probabilities that sum to 1.0):

{{
  "age": {{"distribution": "normal", "mean": 29, "std": 8, "min": 18, "max": 55}},
  "gender": {{"Female": 0.65, "Male": 0.35}},
  "marital_status": {{"Single": 0.45, "Married": 0.48, "Widowed": 0.04, "Divorced": 0.03}},
  "education": {{"No formal education": 0.08, "Primary": 0.15, "Secondary": 0.42, "Tertiary": 0.35}},
  "occupation": {{"Trader": 0.28, "Civil servant": 0.22, "Farmer": 0.15, "Artisan": 0.18, "Unemployed": 0.10, "Others": 0.07}},
  "income_monthly_naira": {{"<30,000": 0.32, "30,000-60,000": 0.31, "60,001-100,000": 0.22, ">100,000": 0.15}},
  "number_of_children": {{"0": 0.20, "1-2": 0.35, "3-4": 0.30, "5+": 0.15}},
  "previous_visits": {{"First visit": 0.25, "2-3 visits": 0.40, "4+ visits": 0.35}}
}}

Adjust the distributions to match the specific population described. Return only JSON."""

    if not key:
        return _default_demographics()

    try:
        from openai import OpenAI
        client   = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        if "age" in data or "gender" in data:
            return data
        return _default_demographics()
    except Exception:
        return _default_demographics()


def _default_demographics() -> dict:
    return {
        "age": {"distribution": "normal", "mean": 29, "std": 8, "min": 18, "max": 55},
        "gender": {"Female": 0.65, "Male": 0.35},
        "marital_status": {"Single": 0.45, "Married": 0.48, "Widowed": 0.04, "Divorced": 0.03},
        "education": {"No formal education": 0.08, "Primary": 0.15, "Secondary": 0.42, "Tertiary": 0.35},
        "occupation": {"Trader": 0.28, "Civil servant": 0.22, "Farmer": 0.15, "Artisan": 0.18, "Unemployed": 0.10, "Others": 0.07},
        "income_monthly_naira": {"<30,000": 0.32, "30,000-60,000": 0.31, "60,001-100,000": 0.22, ">100,000": 0.15},
        "number_of_children": {"0": 0.20, "1-2": 0.35, "3-4": 0.30, "5+": 0.15},
        "previous_visits": {"First visit": 0.25, "2-3 visits": 0.40, "4+ visits": 0.35},
    }


# ══════════════════════════════════════════════════════════════
# Save all study files
# ══════════════════════════════════════════════════════════════

def save_study_files(
    session,
    project_root: Path,
    api_key:      str | None = None,
) -> dict[str, Path]:
    """
    Generate and save all study config files for the dataset pipeline.

    Creates:
        studies/<session_id>/config.json
        studies/<session_id>/questionnaire.json
        studies/<session_id>/demographics.json

    Returns dict of {filename: Path} for all created files.
    """
    from research_engine.writer.chapter_writer import suggest_study_config

    study_name = f"project_{session.session_id}"
    study_dir  = project_root / "studies" / study_name
    study_dir.mkdir(parents=True, exist_ok=True)

    created = {}

    # config.json
    config = suggest_study_config(session)
    p = study_dir / "config.json"
    p.write_text(json.dumps(config, indent=2), encoding="utf-8")
    created["config.json"] = p

    # questionnaire.json
    qdata = build_questionnaire(session, api_key=api_key)
    p = study_dir / "questionnaire.json"
    p.write_text(json.dumps(qdata, indent=2), encoding="utf-8")
    created["questionnaire.json"] = p

    # demographics.json
    ddata = build_demographics(session, api_key=api_key)
    p = study_dir / "demographics.json"
    p.write_text(json.dumps(ddata, indent=2), encoding="utf-8")
    created["demographics.json"] = p

    session.study_config_path = str(study_dir)
    return created
