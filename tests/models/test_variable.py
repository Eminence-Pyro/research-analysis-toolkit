"""
tests/models/test_variable.py

Unit tests for research_engine/models/variable.py
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from research_engine.models.variable import Variable, VariableDictionary, MeasurementScale


class TestVariable:

    def test_variable_creation(self):
        v = Variable(name="age", label="Age of caregiver (years)",
                     scale=MeasurementScale.SCALE)
        assert v.name  == "age"
        assert v.label == "Age of caregiver (years)"
        assert v.scale == MeasurementScale.SCALE

    def test_variable_name_is_snake_case(self):
        v = Variable(name="saq_1", label="Test", scale=MeasurementScale.ORDINAL)
        assert "_" in v.name or v.name.islower()

    def test_variable_repr(self):
        v = Variable(name="gender", label="Gender", scale=MeasurementScale.NOMINAL)
        assert "gender" in repr(v)

    def test_variable_is_derived_default_false(self):
        v = Variable(name="x", label="x", scale=MeasurementScale.SCALE)
        assert v.is_derived is False

    def test_variable_with_allowed_values(self):
        v = Variable(name="gender", label="Gender",
                     scale=MeasurementScale.NOMINAL,
                     allowed_values=["Male", "Female"])
        assert "Male" in v.allowed_values
        assert "Female" in v.allowed_values


class TestVariableDictionary:

    def _make_vd(self):
        return VariableDictionary([
            Variable("respondent_id", "Respondent ID",    MeasurementScale.NOMINAL),
            Variable("age",           "Age (years)",      MeasurementScale.SCALE),
            Variable("gender",        "Gender",           MeasurementScale.NOMINAL),
            Variable("saq1",          "Reception speed",  MeasurementScale.ORDINAL),
        ])

    def test_len(self):
        vd = self._make_vd()
        assert len(vd) == 4

    def test_iteration(self):
        vd = self._make_vd()
        names = [v.name for v in vd]
        assert "age" in names
        assert "gender" in names

    def test_lookup_by_name(self):
        vd = self._make_vd()
        v  = vd["age"]
        assert v.label == "Age (years)"

    def test_lookup_missing_raises_key_error(self):
        vd = self._make_vd()
        with pytest.raises(KeyError):
            _ = vd["nonexistent_variable"]

    def test_labels_dict(self):
        vd = self._make_vd()
        labels = {v.name: v.label for v in vd}
        assert labels["gender"] == "Gender"
