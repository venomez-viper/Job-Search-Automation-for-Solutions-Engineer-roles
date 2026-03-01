# 🎯 Job Hunt Automation

> Automated daily job aggregator that finds 10-15 high-fit Solutions Engineer / Pre-Sales roles in Chicago or Remote, scores them with a near-match AI engine, and emails a digest to you every morning at 8 AM CT.

---

## How It Works

```
Greenhouse + Lever + Ashby + Workable APIs
         ↓
    Filter by title + location
         ↓
    9-Component Scorer
    (title × 3, core skills, tool skills, transferability,
     seniority, location, freshness, ramp boost, hard blockers)
         ↓
    High Match 🟢 / Stretch but Apply 🟡
         ↓
    Deduplicate (SQLite seen-jobs DB)
         ↓
    Top 10-15 jobs → Email + Google Sheet
```

---

## Quick Start (Local)

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/job-hunt-automation.git
cd job-hunt-automation
pip install -r requirements.txt
```

### 2. Set up credentials

```bash
copy .env.example .env
# Then edit .env with your real values (see below)
```

### 3. Run a dry-run (no email sent)

```bash
python main.py --dry-run
```

### 4. Test your email config

```bash
python main.py --email-test
```

### 5. Full run

```bash
python main.py
```

---

## Environment Variables (`.env`)

| Variable | Description |
|---|---|
| `EMAIL_SENDER` | Your Gmail address (e.g. `akashagakash@gmail.com`) |
| `EMAIL_PASSWORD` | Gmail **App Password** (16-char, NOT your regular password) |
| `EMAIL_RECIPIENT` | Where to send the digest (can be same as sender) |
| `GOOGLE_SHEET_ID` | ID from your Google Sheet URL |
| `GOOGLE_CREDENTIALS_JSON` | Full service account JSON (one line) |

### Getting a Gmail App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select **Mail** → **Windows Computer**
3. Copy the 16-character password into `EMAIL_PASSWORD`

> **Note**: 2-Step Verification must be enabled on your Google account.

### Setting Up Google Sheets Logging

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Create a new project (e.g. `job-hunt-automation`)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin → Service Accounts** → Create service account
5. Create a JSON key → download the file
6. Open the JSON file, paste its contents (single line) into `GOOGLE_CREDENTIALS_JSON`
7. Create a Google Sheet at [sheets.google.com](https://sheets.google.com)
8. Share the sheet with the `client_email` from the JSON (give **Editor** access)
9. Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/**SHEET_ID**/edit`

---

## GitHub Actions (Daily at 8 AM CT)

### 1. Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/job-hunt-automation.git
git branch -M main
git add .
git commit -m "Initial job hunt automation setup"
git push -u origin main
```

### 2. Add Repository Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|---|---|
| `EMAIL_SENDER` | Your Gmail address |
| `EMAIL_PASSWORD` | App password (16 chars) |
| `EMAIL_RECIPIENT` | Recipient email |
| `GOOGLE_SHEET_ID` | Google Sheet ID |
| `GOOGLE_CREDENTIALS_JSON` | Full service account JSON (one line) |

### 3. Enable Actions

Go to **Actions** tab in your repo → click **Enable GitHub Actions**.

The workflow runs automatically at **8:00 AM CT** every day. You can also trigger it manually from the **Actions** tab → **Daily Job Hunt** → **Run workflow**.

---

## Customization

All settings are in `config.py`:

| Setting | What it controls |
|---|---|
| `TARGET_TITLES` | Job titles to search for |
| `GREENHOUSE_COMPANIES` | Companies to check on Greenhouse |
| `LEVER_COMPANIES` | Companies to check on Lever |
| `ASHBY_COMPANIES` | Companies to check on Ashby |
| `WORKABLE_COMPANIES` | Companies to check on Workable |
| `CORE_SKILL_WEIGHTS` | Weights for functional skills (demos, APIs, SQL…) |
| `TOOL_SKILL_WEIGHTS` | Weights for tool-specific skills (Snowflake, Tableau…) |
| `TRANSFERABILITY_MAP` | Maps unfamiliar tools → your equivalent experience |
| `RAMP_FEASIBILITY_KEYWORDS` | Signals the company will invest in your growth |
| `HARD_BLOCKER_KEYWORDS` | Disqualifiers (clearances, unreachable certs) |
| `SCORING_WEIGHTS` | Master multipliers for each scoring component |
| `MAX_HIGH_MATCH` | Max "High Match" jobs per day (default: 10) |
| `MAX_STRETCH` | Max "Stretch but Apply" jobs per day (default: 5) |

---

## Project Structure

```
job-hunt-automation/
├── main.py            # Orchestrator
├── config.py          # All tunable parameters
├── scorer.py          # 9-component scoring engine
├── deduper.py         # SQLite seen-jobs DB
├── notifier.py        # Gmail email digest
├── sheets.py          # Google Sheets logger
├── fetchers/
│   ├── base.py        # Job dataclass + helpers
│   ├── greenhouse.py  # Greenhouse public API
│   ├── lever.py       # Lever public API
│   ├── ashby.py       # Ashby GraphQL API
│   └── workable.py    # Workable public API
├── .github/
│   └── workflows/
│       └── daily_jobs.yml  # GitHub Actions schedule
├── requirements.txt
├── .env.example       # Copy → .env and fill in
└── .gitignore
```

---

## Scoring Labels

| Label | Meaning |
|---|---|
| 🟢 **High Match** | Strong functional alignment + good tool overlap. Apply immediately. |
| 🟡 **Stretch but Apply** | Strong functional fit, some tool gap. Your Zoho/SQL/demo experience transfers. Worth applying. |

---

## Adding New Job Sources

1. Create `fetchers/yourplatform.py` following the pattern in `fetchers/greenhouse.py`
2. Import and call it in `main.py` inside the fetcher loop
3. Add company slugs to `config.py`

---

*Built for Akash Anipakalu Giridhar — Solutions Engineer | Pre-Sales | Chicago / Remote*
