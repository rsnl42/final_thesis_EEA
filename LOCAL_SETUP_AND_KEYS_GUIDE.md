# Local Setup & API Keys Configuration Guide

This guide details everything required to clone, install, configure, and execute the **Mapping EdTech Fit in Sub-Saharan Africa** platform and its data pipelines on any local machine or developer environment.

---

## 1. Quick Local Setup in 3 Steps

### Step 1: Install Python Dependencies
Ensure Python 3.10+ (tested through Python 3.14) and `pip` are installed:
```bash
pip install -r requirements.txt
```
*(Dependencies include `pandas`, `numpy`, `matplotlib`, `pyarrow`, `openpyxl`, `python-docx`, `python-pptx`, `python-dotenv`, and `pytest`.)*

### Step 2: Configure Local Environment Variables
Create your local `.env` configuration from the provided template:
```bash
cp .env.example .env
chmod 600 .env
```
*(The `.env` file is gitignored and will never be committed to GitHub.)*

### Step 3: Run the Verification Tests
Verify that all decision models, arithmetic engines, and compilers function properly:
```bash
pytest
```
*Expected: 54 / 54 tests passing.*

---

## 2. API Keys & Data Source Matrix

The project operates under a **hybrid offline/live model**. All models can run offline using cached institutional data, but live updates require specific keys:

| Pipeline / Service | Script | API Key / Token Required? | How to Obtain / Configure |
| :--- | :--- | :--- | :--- |
| **IATI External Aid Flows** | `scripts/fetch_iati_funding.py` | **Yes** (for live refresh)<br>*Offline mode works via cache* | Register for a free API subscription key at [developer.iatistandard.org](https://developer.iatistandard.org) and set `IATI_API_KEY="..."` in `.env`. |
| **KoboToolbox Field Surveys** | `scripts/fetch_kobo_submissions.py` | **Yes** (for live submissions)<br>*Synthetic demo works without keys* | Create an account at [kobotoolbox.org](https://kf.kobotoolbox.org). Obtain your API Token from Account Settings and copy the Asset UIDs for your 4 deployed forms. |
| **IMF GFS COFOG Spending** | `scripts/fetch_imf_cofog.py` | **No** (Open SDMX 3.0 REST API) | Completely open data. `IMF_API_KEY` is optional. |
| **M-Lab Internet QoS Metrics** | `scripts/fetch_mlab.py` | **No** (Open Parquet Manifest) | Public monthly files hosted via GitHub / Google Cloud. No token needed. |
| **World Bank WDI & UNESCO UIS** | `scripts/fetch_6pillars_pipeline.py` | **No** (Open Data APIs) | Public REST endpoints. No token needed. |
| **DPG Directory Link Health** | `scripts/verify_dpg_urls.py` | **No** (HTTP Link Crawler) | Public health-check crawler equipped with polite pacing (1.0s) and exponential retry backoff. |

---

## 3. Detailed `.env` Configuration Reference

Open your `.env` file and configure the parameters as needed:

```ini
# ==============================================================================
# Local Environment Variables
# ==============================================================================

# ── IATI Datastore API ────────────────────────────────────────────────────────
# Solr API Key for querying multilateral and bilateral education aid flows:
IATI_API_KEY="your_iati_primary_key_here"

# ── KoboToolbox Survey Pipeline ───────────────────────────────────────────────
# Typically https://kf.kobotoolbox.org or https://eu.kobotoolbox.org
KOBO_SERVER="https://kf.kobotoolbox.org"

# Your Kobo personal API token (Account Settings -> API Tokens):
KOBO_TOKEN="your_kobo_api_token_here"

# ── 4 Kobo Form Asset UIDs ────────────────────────────────────────────────────
# Found in the browser address bar when viewing each form:
# https://kf.kobotoolbox.org/#/forms/<ASSET_UID>/landing
KOBO_UID_TEACHER="your_teacher_screener_uid"
KOBO_UID_PROVIDER="your_edtech_provider_uid"
KOBO_UID_EXPERT="your_systems_expert_uid"
KOBO_UID_FOLLOWUP="your_followup_contact_uid"
```

---

## 4. How to Run Locally

### Launch the Web Observatory
Serve the project root over HTTP:
```bash
python3 scripts/serve_dev.py 8000
```
Then navigate to `http://localhost:8000/` in any modern web browser.

### Run Pipeline Updates
```bash
# Fetch latest IMF COFOG domestic outlays (2017–2024):
python3 scripts/fetch_imf_cofog.py --since 2017 --force-refresh

# Fetch latest IATI aid transactions using your IATI_API_KEY:
python3 scripts/fetch_iati_funding.py --since 2017 --force-refresh

# Recompile the synthesized Macro-Fiscal Recurrent Cliff dataset:
python3 scripts/compile_macro_fiscal_indicators.py --force-refresh

# Verify all educational DPG URLs:
python3 scripts/verify_dpg_urls.py
```

### Run Kobo Survey Pipeline
* **Live Ingestion (requires configured Kobo credentials):**
  ```bash
  python3 scripts/fetch_kobo_submissions.py --output-dir /tmp/kobo-raw
  python3 scripts/process_kobo_surveys.py --input-dir /tmp/kobo-raw --output data/processed/survey_dashboard_live.json
  ```
* **Offline / Demo Simulation (works without credentials):**
  ```bash
  python3 scripts/fetch_kobo_submissions.py --demo
  ```
