"""
research_engine/models/dataset.py
Stage 1 — Core Domain Model

Defines the Dataset — the complete collection of generated or imported
research data for a study.

    Dataset  — holds all Respondents and exposes methods for analysis,
               iteration, and export

The Dataset is what validators, analysis modules, and exporters receive.
It is the final product of the generation pipeline and the starting point
for the analysis and export pipeline.

Example
-------
    >>> from research_engine.models.dataset import Dataset
    >>> from research_engine.models.respondent import Respondent, Response
    >>>
    >>> ds = Dataset(study_title="Immunization Satisfaction Study", seed=42)
    >>> r1 = Respondent("R001", facility_id=1,
    ...                 demographics={"age": 28, "gender": "Female"})
    >>> r1.add_response(Response("saq1", 4))
    >>> ds.add(r1)
    >>> len(ds)
    1
    >>> ds["R001"].demographics["gender"]
    'Female'
    >>> ds.to_dataframe()[["respondent_id","age","gender","saq1"]].head()
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator

from research_engine.models.respondent import Respondent


class Dataset:
    """
    The complete collection of Respondents for one study run.

    A Dataset is produced by the generation pipeline (Stages 5–7) and
    consumed by the validation, analysis, and export pipelines (Stages 8–10).

    Attributes
    ----------
    study_title : str
        The title of the study this dataset belongs to.

    seed : int | None
        The random seed used to generate this dataset.
        Stored for reproducibility — the same seed + same config
        always produces the same dataset.

    generated_at : datetime
        Timestamp of when this dataset was created.

    notes : str
        Optional free-text notes (generation parameters, version, etc.)
    """

    def __init__(
        self,
        study_title:  str       = "",
        seed:         int | None = None,
        notes:        str       = "",
    ) -> None:
        self.study_title  = study_title
        self.seed         = seed
        self.generated_at = datetime.now()
        self.notes        = notes
        self._respondents: dict[str, Respondent] = {}

    # ── Respondent management ─────────────────────────────────

    def add(self, respondent: Respondent) -> None:
        """
        Add a Respondent to the dataset.
        Raises ValueError if the respondent_id is already present.
        """
        if respondent.respondent_id in self._respondents:
            raise ValueError(
                f"Respondent {respondent.respondent_id!r} is already in this dataset."
            )
        self._respondents[respondent.respondent_id] = respondent

    def get(self, respondent_id: str) -> Respondent | None:
        """Return Respondent by ID, or None if not found."""
        return self._respondents.get(respondent_id)

    @property
    def respondents(self) -> list[Respondent]:
        """All respondents in insertion order."""
        return list(self._respondents.values())

    def by_facility(self, facility_id: int) -> list[Respondent]:
        """All respondents from a given facility."""
        return [r for r in self._respondents.values() if r.facility_id == facility_id]

    # ── Data extraction ───────────────────────────────────────

    def to_records(self) -> list[dict[str, Any]]:
        """
        Return a list of flat dicts — one per respondent.
        Each dict contains demographics + responses + observations.
        This is the format passed to exporters.
        """
        return [r.to_flat_dict() for r in self._respondents.values()]

    def to_dataframe(self):
        """
        Return a pandas DataFrame with one row per respondent.
        Requires pandas to be installed.
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "pandas is required for Dataset.to_dataframe(). "
                "Install it with: pip install pandas"
            ) from exc
        return pd.DataFrame(self.to_records())

    def column_values(self, variable_name: str) -> list[Any]:
        """
        Return a flat list of values for a single variable across all respondents.
        Missing values (is_missing=True) are excluded.
        Useful for computing statistics on one variable at a time.
        """
        values = []
        for respondent in self._respondents.values():
            v = respondent.get_value(variable_name)
            if v is not None:
                values.append(v)
        return values

    def likert_column(self, variable_name: str) -> list[int]:
        """
        Return a list of integer Likert values for a variable, skipping
        non-integer values. Used by analysis modules.
        """
        return [
            int(v) for v in self.column_values(variable_name)
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        ]

    # ── Metadata ──────────────────────────────────────────────

    @property
    def n(self) -> int:
        """Total number of respondents."""
        return len(self._respondents)

    @property
    def facility_ids(self) -> list[int]:
        """Sorted unique list of facility IDs in this dataset."""
        return sorted({r.facility_id for r in self._respondents.values()})

    @property
    def variable_names(self) -> list[str]:
        """
        All variable names present in the dataset.
        Derived from the first respondent's flat dict keys.
        Returns an empty list if the dataset is empty.
        """
        if not self._respondents:
            return []
        first = next(iter(self._respondents.values()))
        return list(first.to_flat_dict().keys())

    def summary(self) -> str:
        """Return a short human-readable summary of the dataset."""
        facilities = ", ".join(str(f) for f in self.facility_ids)
        return (
            f"Dataset: {self.study_title}\n"
            f"  Respondents : {self.n}\n"
            f"  Facilities  : {facilities}\n"
            f"  Variables   : {len(self.variable_names)}\n"
            f"  Generated   : {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  Seed        : {self.seed}\n"
            f"  Notes       : {self.notes or '—'}"
        )

    # ── Dunder methods ────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._respondents)

    def __getitem__(self, respondent_id: str) -> Respondent:
        try:
            return self._respondents[respondent_id]
        except KeyError:
            raise KeyError(f"Respondent {respondent_id!r} not found in Dataset.")

    def __contains__(self, respondent_id: str) -> bool:
        return respondent_id in self._respondents

    def __iter__(self) -> Iterator[Respondent]:
        return iter(self._respondents.values())

    def __repr__(self) -> str:
        return (
            f"Dataset(study={self.study_title!r}, "
            f"n={self.n}, seed={self.seed})"
        )
