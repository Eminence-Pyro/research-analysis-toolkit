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
from research_engine.writer.reference_generator import (
    extract_citations, generate_references, format_reference_list,
    Citation, ReferenceList,
)
from research_engine.writer.questionnaire_builder import (
    build_questionnaire, build_demographics, save_study_files,
)
from research_engine.writer.chapter_writer import revise_chapter
from research_engine.writer.chapter4_bridge import (
    write_chapter4_with_data, build_analysis_context,
)
from research_engine.writer.supervisor_feedback import (
    parse_feedback, apply_feedback, FeedbackItem,
)
from research_engine.writer.context_manager import (
    build_context_summary, compress_chapter, inject_into_prompt,
)
from research_engine.writer.spss_sync import (
    extract_spss_variables, generate_methods_paragraph,
    check_consistency, write_methods_section,
)
