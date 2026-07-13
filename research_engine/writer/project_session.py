"""
research_engine/writer/project_session.py

A ProjectSession holds all the state for one research project.
It is the central object passed between writer modules, parsers, and exporters.

A session is created once (from an uploaded guideline or from scratch),
then populated incrementally as the user requests chapters.

It is serialisable to / from JSON so it can be saved to disk between runs.

Public API
----------
    ProjectSession.new(title, level, topic)      → ProjectSession
    ProjectSession.from_file(path)               → ProjectSession
    session.save(path)                           → Path
    session.set_chapter(n, content)              → None
    session.get_chapter(n)                       → ChapterContent | None
    session.is_complete                          → bool
    session.summary()                            → str
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


# ── Education level → writing style ──────────────────────────

class EducationLevel(str, Enum):
    OND       = "ond"
    HND       = "hnd"
    BSC       = "bsc"       # undergraduate
    PGD       = "pgd"
    MSC       = "msc"       # postgraduate taught
    PHD       = "phd"       # doctoral
    UNKNOWN   = "unknown"

    @classmethod
    def detect(cls, raw: str) -> "EducationLevel":
        """Detect level from free text (e.g. 'B.Sc', 'Master of Science')."""
        raw = raw.lower().strip()
        if any(x in raw for x in ["phd", "doctorate", "doctoral", "d.phil"]):
            return cls.PHD
        if any(x in raw for x in ["msc", "master", "m.sc", "m.a.", "pgd", "postgrad"]):
            return cls.MSC
        if any(x in raw for x in ["bsc", "bachelor", "b.sc", "b.a.", "degree", "undergrad", "hons"]):
            return cls.BSC
        if any(x in raw for x in ["hnd", "higher national"]):
            return cls.HND
        if any(x in raw for x in ["ond", "ordinary national"]):
            return cls.OND
        return cls.UNKNOWN


class ResearchDesign(str, Enum):
    DESCRIPTIVE        = "descriptive"
    CORRELATIONAL      = "correlational"
    EXPERIMENTAL       = "experimental"
    QUASI_EXPERIMENTAL = "quasi_experimental"
    CROSS_SECTIONAL    = "cross_sectional"
    LONGITUDINAL       = "longitudinal"
    CASE_STUDY         = "case_study"
    MIXED_METHODS      = "mixed_methods"
    UNKNOWN            = "unknown"


# ── Chapter content ───────────────────────────────────────────

@dataclass
class ChapterContent:
    """
    Holds the written content of one chapter.

    number      : 1–5
    title       : e.g. "Introduction"
    content     : the full written text (markdown)
    word_count  : approximate word count
    generated_at: ISO timestamp of last generation
    model_notes : any notes from the AI about assumptions made
    """
    number:       int
    title:        str
    content:      str
    word_count:   int        = 0
    generated_at: str        = ""
    model_notes:  str        = ""
    status:       str        = "draft"   # draft | reviewed | final

    def __post_init__(self):
        if not self.word_count:
            self.word_count = len(self.content.split())
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat()

    def preview(self, chars: int = 300) -> str:
        lines = self.content.strip().split("\n")
        text  = " ".join(l.strip() for l in lines if l.strip())
        return text[:chars] + ("…" if len(text) > chars else "")


CHAPTER_TITLES = {
    1: "Introduction",
    2: "Literature Review",
    3: "Research Methodology",
    4: "Data Presentation and Analysis",
    5: "Summary, Conclusion and Recommendations",
}


# ── Project metadata ──────────────────────────────────────────

@dataclass
class ProjectMetadata:
    """
    All the things we know about the project before writing begins.
    Populated from the uploaded guideline, user input, or AI extraction.
    """
    title:              str           = ""
    topic:              str           = ""
    level:              EducationLevel= EducationLevel.UNKNOWN
    institution:        str           = ""
    department:         str           = ""
    supervisor:         str           = ""
    student_name:       str           = ""
    year:               str           = ""
    word_count_target:  int           = 0    # 0 = auto from level
    citation_style:     str           = "APA"  # APA | Vancouver | Harvard | Chicago
    research_design:    ResearchDesign= ResearchDesign.UNKNOWN
    population:         str           = ""
    study_area:         str           = ""
    key_variables:      list[str]     = field(default_factory=list)
    objectives:         list[str]     = field(default_factory=list)
    research_questions: list[str]     = field(default_factory=list)
    hypotheses:         list[str]     = field(default_factory=list)
    keywords:           list[str]     = field(default_factory=list)

    def word_count_for_level(self) -> dict[int, int]:
        """Return recommended word counts per chapter for this education level."""
        targets = {
            EducationLevel.OND:     {1:1500, 2:2000, 3:1500, 4:2500, 5:1000},
            EducationLevel.HND:     {1:2000, 2:2500, 3:2000, 4:3000, 5:1500},
            EducationLevel.BSC:     {1:2500, 2:4000, 3:2500, 4:4000, 5:2000},
            EducationLevel.PGD:     {1:3000, 2:5000, 3:3000, 4:5000, 5:2500},
            EducationLevel.MSC:     {1:4000, 2:8000, 3:4000, 4:6000, 5:3000},
            EducationLevel.PHD:     {1:5000, 2:15000, 3:5000, 4:8000, 5:4000},
            EducationLevel.UNKNOWN: {1:2500, 2:4000, 3:2500, 4:4000, 5:2000},
        }
        return targets.get(self.level, targets[EducationLevel.UNKNOWN])


# ══════════════════════════════════════════════════════════════
# ProjectSession
# ══════════════════════════════════════════════════════════════

@dataclass
class ProjectSession:
    """
    The central state object for one research project.

    A session encapsulates:
      - metadata extracted from the guideline / user input
      - the uploaded files (as text content)
      - chapter contents generated so far
      - the study config (if dataset generation is needed)
      - the analysis results (if pipeline has been run)

    It is JSON-serialisable so it can be saved between sessions.
    """
    session_id:        str                      = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at:        str                      = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at:        str                      = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata:          ProjectMetadata          = field(default_factory=ProjectMetadata)
    chapters:          dict[int, ChapterContent]= field(default_factory=dict)
    uploaded_files:    dict[str, str]           = field(default_factory=dict)  # filename → text content
    guideline_raw:     str                      = ""    # raw text of uploaded guideline
    study_config_path: str                      = ""    # path to generated study config dir
    pipeline_run:      bool                     = False
    notes:             list[str]                = field(default_factory=list)

    # ── Factories ─────────────────────────────────────────────

    @classmethod
    def new(cls,
            title:   str = "",
            level:   str = "",
            topic:   str = "") -> "ProjectSession":
        """Create a new blank session."""
        meta = ProjectMetadata(
            title = title,
            topic = topic,
            level = EducationLevel.detect(level) if level else EducationLevel.UNKNOWN,
        )
        return cls(metadata=meta)

    @classmethod
    def from_file(cls, path: str | Path) -> "ProjectSession":
        """Load a saved session from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls._from_dict(data)

    # ── Persistence ───────────────────────────────────────────

    def save(self, path: str | Path) -> Path:
        """Save the session to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.utcnow().isoformat()
        path.write_text(json.dumps(self._to_dict(), indent=2, ensure_ascii=False),
                        encoding="utf-8")
        return path

    # ── Chapter management ────────────────────────────────────

    def set_chapter(self, number: int, content: str,
                    notes: str = "", status: str = "draft") -> None:
        """Store or replace a chapter's content."""
        if number not in range(1, 6):
            raise ValueError(f"Chapter number must be 1–5, got {number}")
        self.chapters[number] = ChapterContent(
            number      = number,
            title       = CHAPTER_TITLES.get(number, f"Chapter {number}"),
            content     = content,
            model_notes = notes,
            status      = status,
        )
        self.updated_at = datetime.utcnow().isoformat()

    def get_chapter(self, number: int) -> ChapterContent | None:
        return self.chapters.get(number)

    def add_file(self, filename: str, text_content: str) -> None:
        """Store uploaded file content (already extracted to text)."""
        self.uploaded_files[filename] = text_content
        self.updated_at = datetime.utcnow().isoformat()

    # ── Properties ────────────────────────────────────────────

    @property
    def is_complete(self) -> bool:
        return all(n in self.chapters for n in range(1, 6))

    @property
    def chapters_done(self) -> list[int]:
        return sorted(self.chapters.keys())

    @property
    def chapters_remaining(self) -> list[int]:
        return [n for n in range(1, 6) if n not in self.chapters]

    # ── Summary ───────────────────────────────────────────────

    def summary(self) -> str:
        m = self.metadata
        done  = self.chapters_done
        left  = self.chapters_remaining
        lines = [
            f"Session {self.session_id}",
            f"  Title   : {m.title or '(untitled)'}",
            f"  Level   : {m.level.value.upper()}",
            f"  Design  : {m.research_design.value}",
            f"  Created : {self.created_at[:10]}",
            f"  Files   : {list(self.uploaded_files.keys()) or 'none'}",
            f"  Chapters: {done or 'none'} done, {left} remaining",
            f"  Pipeline: {'run' if self.pipeline_run else 'not run'}",
        ]
        return "\n".join(lines)

    # ── Serialisation (private) ────────────────────────────────

    def _to_dict(self) -> dict:
        d = asdict(self)
        # Convert enums to strings
        d["metadata"]["level"]           = self.metadata.level.value
        d["metadata"]["research_design"] = self.metadata.research_design.value
        # Convert int keys to str for JSON
        d["chapters"] = {str(k): v for k, v in d["chapters"].items()}
        return d

    @classmethod
    def _from_dict(cls, d: dict) -> "ProjectSession":
        meta_d = d.get("metadata", {})
        meta   = ProjectMetadata(
            title              = meta_d.get("title", ""),
            topic              = meta_d.get("topic", ""),
            level              = EducationLevel(meta_d.get("level", "unknown")),
            institution        = meta_d.get("institution", ""),
            department         = meta_d.get("department", ""),
            supervisor         = meta_d.get("supervisor", ""),
            student_name       = meta_d.get("student_name", ""),
            year               = meta_d.get("year", ""),
            word_count_target  = meta_d.get("word_count_target", 0),
            citation_style     = meta_d.get("citation_style", "APA"),
            research_design    = ResearchDesign(meta_d.get("research_design", "unknown")),
            population         = meta_d.get("population", ""),
            study_area         = meta_d.get("study_area", ""),
            key_variables      = meta_d.get("key_variables", []),
            objectives         = meta_d.get("objectives", []),
            research_questions = meta_d.get("research_questions", []),
            hypotheses         = meta_d.get("hypotheses", []),
            keywords           = meta_d.get("keywords", []),
        )
        chapters = {}
        for k, v in d.get("chapters", {}).items():
            chapters[int(k)] = ChapterContent(**v)

        return cls(
            session_id        = d.get("session_id", str(uuid.uuid4())[:8]),
            created_at        = d.get("created_at", datetime.utcnow().isoformat()),
            updated_at        = d.get("updated_at", datetime.utcnow().isoformat()),
            metadata          = meta,
            chapters          = chapters,
            uploaded_files    = d.get("uploaded_files", {}),
            guideline_raw     = d.get("guideline_raw", ""),
            study_config_path = d.get("study_config_path", ""),
            pipeline_run      = d.get("pipeline_run", False),
            notes             = d.get("notes", []),
        )
