"""
research_engine/writer/__init__.py

The writer module — AI-powered chapter generation for research projects.

Public API
----------
    from research_engine.writer import (
        ProjectSession,
        ProjectMetadata,
        EducationLevel,
        ResearchDesign,
        extract_text,
        parse_guideline,
        write_chapter,
        extract_metadata_with_ai,
        suggest_study_config,
    )
"""
from research_engine.writer.project_session import (
    ProjectSession,
    ProjectMetadata,
    ChapterContent,
    EducationLevel,
    ResearchDesign,
    CHAPTER_TITLES,
)
from research_engine.writer.guideline_parser import (
    extract_text,
    parse_guideline,
    extract_objectives,
    extract_research_questions,
    extract_hypotheses,
)
from research_engine.writer.chapter_writer import (
    write_chapter,
    extract_metadata_with_ai,
    suggest_study_config,
)

__all__ = [
    "ProjectSession",
    "ProjectMetadata",
    "ChapterContent",
    "EducationLevel",
    "ResearchDesign",
    "CHAPTER_TITLES",
    "extract_text",
    "parse_guideline",
    "extract_objectives",
    "extract_research_questions",
    "extract_hypotheses",
    "write_chapter",
    "extract_metadata_with_ai",
    "suggest_study_config",
]
