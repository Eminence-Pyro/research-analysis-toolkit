"""
tests/workflow/test_pipeline.py

Integration test — full Pipeline run against immunization_aba study.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

STUDY_DIR = Path(__file__).parent.parent.parent / "studies" / "immunization_aba"

@pytest.mark.skipif(not STUDY_DIR.exists(), reason="immunization_aba study not found")
class TestPipeline:

    def setup_method(self):
        # Fresh pipeline for each test
        from research_engine.workflow import Pipeline
        self.Pipeline = Pipeline

    def test_load(self):
        p = self.Pipeline(STUDY_DIR, seed=42)
        p.load()
        assert p.bundle is not None
        assert p.bundle.study.target_n == 120

    def test_generate(self):
        p = self.Pipeline(STUDY_DIR, seed=42)
        p.generate()
        assert p.dataset is not None
        assert len(p.dataset) == 120

    def test_validate(self):
        p = self.Pipeline(STUDY_DIR, seed=42)
        p.validate()
        assert p.report is not None
        assert p.report.is_ready is True

    def test_validate_14_checks(self):
        p = self.Pipeline(STUDY_DIR, seed=42)
        p.validate()
        assert len(p.report.checks) == 14

    def test_full_run_produces_files(self, tmp_path):
        from studies.immunization_aba.run import ORDINAL_MAPS, SPSS_MAPS, CROSSTAB_PAIRS
        p = self.Pipeline(
            study_dir      = STUDY_DIR,
            output_dir     = tmp_path,
            seed           = 42,
            ordinal_maps   = ORDINAL_MAPS,
            spss_maps      = SPSS_MAPS,
            crosstab_pairs = CROSSTAB_PAIRS,
        )
        p.export()
        assert len(p.output_files) == 3
        for f in p.output_files:
            assert f.exists()
            assert f.stat().st_size > 0
