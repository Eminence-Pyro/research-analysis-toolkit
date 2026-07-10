"""
config.py — Study-specific configuration for:
  "Pattern of Patient (Caregiver) Satisfaction with Immunization Services
   at Urban Primary Health Centers in Wards I–IV, Aba North LGA, Abia State"

To adapt this generator for a different study, copy this folder, rename it,
and update the constants below and the questionnaire.json / demographics.json files.
"""

STUDY_TITLE      = "Pattern of Caregiver Satisfaction with Immunization Services"
STUDY_SETTING    = "Urban PHCs, Wards I–IV, Aba North LGA, Abia State"
STUDY_POPULATION = "Caregivers of children 0–23 months attending immunization clinics"
N_RESPONDENTS    = 120
SEED_DEFAULT     = 42

FACILITIES = [
    {"id": 1, "name": "Ward I PHC",  "ward": "I"},
    {"id": 2, "name": "Ward II PHC", "ward": "II"},
    {"id": 3, "name": "Ward III PHC","ward": "III"},
    {"id": 4, "name": "Ward IV PHC", "ward": "IV"},
]
RESPONDENTS_PER_FACILITY = 30          # must equal N_RESPONDENTS / len(FACILITIES)

# Facility-level fixed effects on satisfaction (small adjustments, ±0.5 max)
FACILITY_EFFECTS = {1: 0.3, 2: 0.0, 3: 0.2, 4: -0.1}
