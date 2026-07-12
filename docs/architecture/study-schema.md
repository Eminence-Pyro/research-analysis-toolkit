# Study Schema Reference (v1.0)

Each study lives in `studies/<study_name>/` and is defined by four JSON files.
All four must include `"schema_version": "1.0"`.

## File overview

| File | Purpose |
|------|---------|
| `config.json` | Study metadata, facilities, target N |
| `questionnaire.json` | Sections and Likert items |
| `demographics.json` | Population distributions |
| `observation.json` | Facility checklist items |

---

## config.json

```json
{
  "schema_version": "1.0",
  "title": "Pattern of Caregiver Satisfaction ...",
  "design": "Cross-sectional",
  "setting": "Urban PHCs, Aba North LGA",
  "population": "Caregivers of children 0-23 months",
  "sampling_technique": "Consecutive sampling",
  "target_n": 120,
  "facilities": [
    { "id": 1, "name": "Ward I PHC",  "satisfaction_effect":  0.3 },
    { "id": 2, "name": "Ward II PHC", "satisfaction_effect":  0.0 }
  ]
}
```

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `schema_version` | ✅ | string | Always `"1.0"` |
| `title` | ✅ | string | |
| `design` | ✅ | string | Cross-sectional, Cohort, etc. |
| `target_n` | ✅ | integer | Required sample size |
| `facilities[].id` | ✅ | integer | Unique per study |
| `facilities[].satisfaction_effect` | ✅ | float | Causal model offset ±0–0.5 |

---

## questionnaire.json

```json
{
  "schema_version": "1.0",
  "sections": {
    "A": {
      "title": "Satisfaction with Reception",
      "items": [
        { "number": "A1", "variable_name": "saq1",
          "text": "Registration was quick and efficient.", "scale": "Likert5" }
      ]
    }
  }
}
```

---

## demographics.json

```json
{
  "schema_version": "1.0",
  "variables": [
    { "name": "age", "distribution": "normal",
      "params": { "mean": 27, "std": 6, "min": 15, "max": 55 }, "type": "continuous" },
    { "name": "gender", "distribution": "categorical",
      "params": { "Female": 0.78, "Male": 0.22 }, "type": "categorical" }
  ]
}
```

Supported distributions: `normal`, `exponential`, `categorical`, `uniform`

---

## observation.json

```json
{
  "schema_version": "1.0",
  "checklist": [
    { "variable_name": "cleanliness", "label": "Facility is visibly clean",
      "anchor": "environment", "base_probability": 0.7 }
  ]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `anchor` | ✅ | `"environment"` or `"service"` |
| `base_probability` | ✅ | Baseline P(Yes) |
| `distance_sensitive` | — | If true, P(Yes) decreases with distance |
