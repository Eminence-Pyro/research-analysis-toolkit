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
from research_engine.writer.ocr_parser import (
    extract_text_with_ocr, is_scanned_pdf, ocr_pdf,
)
from research_engine.writer.citation_diversity import (
    score_citation_diversity, score_session, suggest_improvements,
    CitationDiversityReport,
)
from research_engine.writer.similarity_estimator import (
    estimate_similarity, estimate_session, flag_generic_sentences,
    SimilarityReport,
)
from research_engine.writer.study_comparison import (
    compare_sessions, render_comparison_table, ComparisonReport,
)
from research_engine.writer.apa_formatter import (
    format_apa_reference, format_apa_reference_list,
    build_apa_reference, parse_apa_reference,
)
from research_engine.writer.reference_manager import (
    export_bibtex, export_ris, import_bibtex, import_ris,
    export_to_zotero, export_to_mendeley,
)
