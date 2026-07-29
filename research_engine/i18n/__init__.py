"""
research_engine/i18n/__init__.py
Tier 3 — Multi-language support framework

Provides a lightweight internationalisation layer so the toolkit
can generate chapter content and UI labels in multiple languages.

Currently supported:
  - English (default)
  - French (partial)
  - Yoruba (partial)
  - Igbo (partial)
  - Hausa (partial)

The framework is designed so new languages can be added by dropping
a new translation file into the languages/ directory.

Public API
----------
    get_string(key, lang="en")           → str
    set_language(lang)                   → None
    get_language()                       → str
    list_languages()                     → list[str]
    get_chapter_prompt_template(lang)    → str
    get_section_heading(section, lang)   → str
    register_language(code, name, translations)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════
# Language registry
# ══════════════════════════════════════════════════════════════

@dataclass
class Language:
    """A supported language with its translations."""
    code:          str
    name:          str
    native_name:   str
    translations:  dict[str, str] = field(default_factory=dict)
    chapter_headings: dict[str, str] = field(default_factory=dict)
    prompt_template:  str = ""


# ══════════════════════════════════════════════════════════════
# Built-in translations
# ══════════════════════════════════════════════════════════════

_ENGLISH = Language(
    code="en", name="English", native_name="English",
    translations={
        "app_title": "Research Analysis Toolkit",
        "new_project": "New Project",
        "write_chapter": "Write Chapter",
        "export_project": "Export Project",
        "references": "References",
        "abstract": "Abstract",
        "introduction": "Introduction",
        "literature_review": "Literature Review",
        "methodology": "Methodology",
        "results": "Results",
        "discussion": "Discussion",
        "conclusion": "Conclusion",
        "summary": "Summary",
        "recommendations": "Recommendations",
        "table": "Table",
        "figure": "Figure",
        "appendix": "Appendix",
        "questionnaire": "Questionnaire",
        "respondents": "Respondents",
        "total": "Total",
        "frequency": "Frequency",
        "percentage": "Percentage",
        "mean": "Mean",
        "standard_deviation": "Standard Deviation",
        "chapter": "Chapter",
        "background": "Background of the Study",
        "statement_of_problem": "Statement of the Problem",
        "objectives": "Objectives of the Study",
        "research_questions": "Research Questions",
        "hypotheses": "Hypotheses",
        "scope": "Scope of the Study",
        "significance": "Significance of the Study",
        "population": "Population of the Study",
        "sample_size": "Sample Size",
        "sampling_technique": "Sampling Technique",
        "instrument": "Instrument for Data Collection",
        "validity": "Validity of the Instrument",
        "reliability": "Reliability of the Instrument",
        "method_of_analysis": "Method of Data Analysis",
        "presentation": "Presentation of Results",
        "interpretation": "Interpretation of Results",
        "limitations": "Limitations of the Study",
        "contribution": "Contribution to Knowledge",
        "further_research": "Suggestions for Further Research",
    },
    chapter_headings={
        "ch1": "Chapter One: Introduction",
        "ch2": "Chapter Two: Literature Review",
        "ch3": "Chapter Three: Methodology",
        "ch4": "Chapter Four: Results and Discussion",
        "ch5": "Chapter Five: Summary, Conclusion and Recommendations",
    },
    prompt_template=(
        "You are an expert academic research writer specialising in Nigerian "
        "and African university research projects. Write in clear, formal "
        "academic English with proper structure, citations, and analytical depth."
    ),
)

_FRENCH = Language(
    code="fr", name="French", native_name="Français",
    translations={
        "app_title": "Boîte à outils d'analyse de recherche",
        "new_project": "Nouveau projet",
        "write_chapter": "Rédiger un chapitre",
        "export_project": "Exporter le projet",
        "references": "Références",
        "abstract": "Résumé",
        "introduction": "Introduction",
        "literature_review": "Revue de la littérature",
        "methodology": "Méthodologie",
        "results": "Résultats",
        "discussion": "Discussion",
        "conclusion": "Conclusion",
        "summary": "Sommaire",
        "recommendations": "Recommandations",
        "table": "Tableau",
        "figure": "Figure",
        "appendix": "Annexe",
        "questionnaire": "Questionnaire",
        "respondents": "Répondants",
        "total": "Total",
        "frequency": "Fréquence",
        "percentage": "Pourcentage",
        "mean": "Moyenne",
        "standard_deviation": "Écart-type",
        "chapter": "Chapitre",
        "background": "Contexte de l'étude",
        "statement_of_problem": "Énoncé du problème",
        "objectives": "Objectifs de l'étude",
        "research_questions": "Questions de recherche",
        "hypotheses": "Hypothèses",
        "scope": "Portée de l'étude",
        "significance": "Importance de l'étude",
        "population": "Population de l'étude",
        "sample_size": "Taille de l'échantillon",
        "sampling_technique": "Technique d'échantillonnage",
        "instrument": "Instrument de collecte de données",
        "validity": "Validité de l'instrument",
        "reliability": "Fiabilité de l'instrument",
        "method_of_analysis": "Méthode d'analyse des données",
        "presentation": "Présentation des résultats",
        "interpretation": "Interprétation des résultats",
        "limitations": "Limites de l'étude",
        "contribution": "Contribution à la connaissance",
        "further_research": "Suggestions pour les recherches futures",
    },
    chapter_headings={
        "ch1": "Chapitre Un: Introduction",
        "ch2": "Chapitre Deux: Revue de la littérature",
        "ch3": "Chapitre Trois: Méthodologie",
        "ch4": "Chapitre Quatre: Résultats et Discussion",
        "ch5": "Chapitre Cinq: Sommaire, Conclusion et Recommandations",
    },
    prompt_template=(
        "Vous êtes un rédacteur académique expert spécialisé dans les projets "
        "de recherche universitaires africains. Rédigez en français académique "
        "formel avec une structure appropriée, des citations et une profondeur analytique."
    ),
)

_YORUBA = Language(
    code="yo", name="Yoruba", native_name="Yorùbá",
    translations={
        "app_title": "Àràdá Ohun Àbáyọ Iwádìí",
        "chapter": "Ibí",
        "introduction": "Ìfáàrà",
        "literature_review": "Ìtúpalẹ̀ Ìwé",
        "methodology": "Ìlànà Iwádìí",
        "results": "Èsì",
        "conclusion": "Ìparí",
        "table": "Tábìlì",
        "references": "Ìwé Ìtọ́kasi",
        "population": "Àwọn ènìyàn",
        "sample_size": "Ìwọn Àyẹ̀wò",
        "questionnaire": "Ìbéèrè",
        "respondents": "Àwọn olèdìí",
    },
    chapter_headings={
        "ch1": "Ibí Kìíní: Ìfáàrà",
        "ch2": "Ibí Kejì: Ìtúpalẹ̀ Ìwé",
        "ch3": "Ibí Kẹta: Ìlànà Iwádìí",
        "ch4": "Ibí Kẹrin: Èsì àti Ìjíròrò",
        "ch5": "Ibí Karùn-ún: Ìparí àti Ìdààbọ",
    },
    prompt_template=(
        "Ìwọ jẹ́ onímọ̀ nínú ìkọ̀wé iwádìí ẹ̀kọ́ nípa àwọn ilé-ìwé gíga Nàìjíríà. "
        "Kọ́ ní Yorùbá àti pé kí o lo ìlànà ìkọ̀wé àdáni."
    ),
)

_IGBO = Language(
    code="ig", name="Igbo", native_name="Igbo",
    translations={
        "app_title": "Ngwaọrụ Nnyocha Mmadụ",
        "chapter": "Isi",
        "introduction": "Nweta",
        "literature_review": "Nnyocha Akwụkwọ",
        "methodology": "Usoro Nnyocha",
        "results": "Nsonaazu",
        "conclusion": "Mmechi",
        "table": "Tebụl",
        "references": "Ntụaka",
        "population": "Ndị mmadụ",
        "sample_size": "Ọnụọgụ Nnyocha",
        "questionnaire": "Ajụjụ",
        "respondents": "Ndị zara ajụjụ",
    },
    chapter_headings={
        "ch1": "Isi nke Mbụ: Nweta",
        "ch2": "Isi nke Abụọ: Nnyocha Akwụkwọ",
        "ch3": "Isi nke Atọ: Usoro Nnyocha",
        "ch4": "Isi nke Anọ: Nsonaazu na Mkparịtaụka",
        "ch5": "Isi nke Ise: Mmechi na Ntuziaka",
    },
    prompt_template=(
        "Ị bụ ọkachamara n'ide akwụkwọ nyocha mahadum Naijiria. "
        "Dee n'asụsụ Igbo na nke ọma."
    ),
)

_HAUSA = Language(
    code="ha", name="Hausa", native_name="Hausa",
    translations={
        "app_title": "Kayan Aikin Binciken Kimiyya",
        "chapter": "Babi",
        "introduction": "Gabatarwa",
        "literature_review": "Dubawa Littattafai",
        "methodology": "Hanyar Bincike",
        "results": "Sakamako",
        "conclusion": "Kammalawa",
        "table": "Tebur",
        "references": "Turbawa",
        "population": "Yawan Jama'a",
        "sample_size": "Girman Samfurin",
        "questionnaire": "Tambayoyi",
        "respondents": "Masu amsa",
    },
    chapter_headings={
        "ch1": "Babi na Daya: Gabatarwa",
        "ch2": "Babi na Biyu: Dubawa Littattafai",
        "ch3": "Babi na Uku: Hanyar Bincike",
        "ch4": "Babi na Hudu: Sakamako da Tattaunawa",
        "ch5": "Babi na Biyar: Kammalawa da Shawarwari",
    },
    prompt_template=(
        "Kai ƙwararre ne wajen rubuta bincike na jami'o'i a Najeriya. "
        "Rubu da Hausa cikin tsari da kyau."
    ),
)


# ══════════════════════════════════════════════════════════════
# Global state
# ══════════════════════════════════════════════════════════════

_languages: dict[str, Language] = {
    "en": _ENGLISH,
    "fr": _FRENCH,
    "yo": _YORUBA,
    "ig": _IGBO,
    "ha": _HAUSA,
}
_current_language: str = "en"


def set_language(lang: str) -> None:
    """Set the active language."""
    global _current_language
    if lang in _languages:
        _current_language = lang
    else:
        raise ValueError(f"Language '{lang}' not supported. Available: {list_languages()}")


def get_language() -> str:
    """Get the current active language code."""
    return _current_language


def list_languages() -> list[str]:
    """List all available language codes."""
    return sorted(_languages.keys())


def get_language_info(lang: str = None) -> Language:
    """Get the full Language object for a given code."""
    code = lang or _current_language
    return _languages.get(code, _ENGLISH)


def register_language(code: str, name: str, native_name: str,
                       translations: dict, chapter_headings: dict = None,
                       prompt_template: str = "") -> None:
    """Register a new language at runtime."""
    _languages[code] = Language(
        code=code, name=name, native_name=native_name,
        translations=translations,
        chapter_headings=chapter_headings or {},
        prompt_template=prompt_template
    )


def get_string(key: str, lang: str = None) -> str:
    """Get a translated string for a given key."""
    code = lang or _current_language
    language = _languages.get(code, _ENGLISH)
    return language.translations.get(key, _ENGLISH.translations.get(key, key))


def get_chapter_heading(chapter_num: int, lang: str = None) -> str:
    """Get the heading for a chapter number in the given language."""
    code = lang or _current_language
    language = _languages.get(code, _ENGLISH)
    key = f"ch{chapter_num}"
    return language.chapter_headings.get(key, _ENGLISH.chapter_headings.get(key, f"Chapter {chapter_num}"))


def get_chapter_prompt_template(lang: str = None) -> str:
    """Get the LLM prompt template for a given language."""
    code = lang or _current_language
    language = _languages.get(code, _ENGLISH)
    return language.prompt_template or _ENGLISH.prompt_template
