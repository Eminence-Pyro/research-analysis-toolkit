"""
tests/models/test_questionnaire.py

Unit tests for research_engine/models/questionnaire.py
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from research_engine.models.questionnaire import Question, Section, Questionnaire


class TestQuestion:

    def test_question_creation(self):
        q = Question(number="A1", variable_name="saq1",
                     text="Registration was quick.", scale="Likert5")
        assert q.number        == "A1"
        assert q.variable_name == "saq1"
        assert q.scale         == "Likert5"

    def test_question_repr(self):
        q = Question("A1", "saq1", "Registration was quick.", "Likert5")
        assert "A1" in repr(q)


class TestSection:

    def _make_section(self):
        q1 = Question("A1", "saq1", "Item one",   "Likert5")
        q2 = Question("A2", "saq2", "Item two",   "Likert5")
        q3 = Question("A3", "saq3", "Item three", "Likert5")
        return Section(key="A", title="Reception", questions=[q1, q2, q3])

    def test_section_question_count(self):
        s = self._make_section()
        assert len(s.questions) == 3

    def test_section_variable_names(self):
        s = self._make_section()
        names = [q.variable_name for q in s.questions]
        assert "saq1" in names
        assert "saq3" in names


class TestQuestionnaire:

    def _make_questionnaire(self):
        sections = [
            Section("A", "Reception", [
                Question("A1", "saq1", "Item A1", "Likert5"),
                Question("A2", "saq2", "Item A2", "Likert5"),
            ]),
            Section("B", "Services", [
                Question("B1", "sbq1", "Item B1", "Likert5"),
            ]),
        ]
        return Questionnaire(title="Test Questionnaire", sections=sections)

    def test_question_count(self):
        q = self._make_questionnaire()
        assert q.question_count == 3

    def test_all_questions_flat(self):
        q    = self._make_questionnaire()
        all_q = q.all_questions
        assert len(all_q) == 3

    def test_section_keys(self):
        q = self._make_questionnaire()
        keys = [s.key for s in q.sections]
        assert "A" in keys
        assert "B" in keys
