"""
config.py — Central configuration for the Job Hunt Automation system.
Edit this file to tune your job search preferences.
"""

# ─── Target Role Keywords ────────────────────────────────────────────────────
TARGET_TITLES = [
    "solutions engineer",
    "sales engineer",
    "solution consultant",
    "presales engineer",
    "pre-sales engineer",
    "pre sales engineer",
    "technical sales engineer",
    "solutions consultant",
    "technical solutions engineer",
    "customer solutions engineer",
    "associate solutions engineer",
    "jr solutions engineer",
    "junior solutions engineer",
]

# ─── Location Filters ────────────────────────────────────────────────────────
ALLOWED_LOCATIONS = [
    "chicago",
    "remote",
    "united states",
    "us",
    "nationwide",
    "",  # blank location often means remote
]

# ─── Seniority Exclusions (skip these) ───────────────────────────────────────
EXCLUDE_TITLE_KEYWORDS = [
    "principal",
    "staff",
    "director",
    "vp ",
    "vice president",
    "senior staff",
    "distinguished",
    "head of",
    "manager",
    "lead",      # optional: remove if you want Lead roles
]

# ─── Scoring Architecture ───────────────────────────────────────────────────
# The scorer applies 5 independent components, each with its own max weight.
# Final score = title_score + description_score + seniority_score + location_score + freshness_score
#
# MASTER COMPONENT WEIGHTS — scale each component's contribution.
SCORING_WEIGHTS = {
    "title_multiplier": 3,        # title keyword matches count 3× vs description
    "description_multiplier": 1,  # baseline
    "seniority_max_penalty": -15,  # floor for seniority penalty
    "location_chicago_bonus": 8,   # strong pref for Chicago
    "location_remote_bonus": 5,    # remote is also good
    "location_other_penalty": -10, # clearly wrong location
    "freshness_7d_bonus": 5,       # posted within 7 days
    "freshness_14d_bonus": 2,      # posted within 14 days
    "freshness_30d_penalty": -3,   # posted 30+ days ago
    "freshness_unknown": 0,        # no date = neutral
}

# ─── Title Role Match Weights ─────────────────────────────────────────────────
# Applied when keyword found specifically in the JOB TITLE (not just description).
# Scores here are BEFORE multiplier is applied.
TITLE_KEYWORD_WEIGHTS = {
    # Exact target roles — highest signal
    "solutions engineer": 20,
    "solution engineer": 20,
    "pre-sales engineer": 18,
    "presales engineer": 18,
    "sales engineer": 16,
    "solution consultant": 15,
    "solutions consultant": 15,
    "technical sales engineer": 15,
    # Adjacent roles — good signal
    "technical consultant": 8,
    "customer success engineer": 7,
    "implementation engineer": 7,
    "integration engineer": 7,
    "field engineer": 6,
    "platform engineer": 4,
    "product specialist": 4,
    "technical specialist": 5,
    "technical account": 5,
    "associate solutions": 12,
    "junior solutions": 12,
    "enterprise solutions": 14,
}

# ─── Adjacent Role Boosts (description-level) ────────────────────────────────
ADJACENT_ROLE_KEYWORDS = [
    "technical consultant",
    "customer success engineer",
    "implementation engineer",
    "integration specialist",
    "technical account manager",
    "field engineer",
    "enterprise architect",
    "solution architect",
]

# ─── Unrelated Role Penalties ────────────────────────────────────────────────
# Applied when the job title clearly belongs to a different domain.
UNRELATED_ROLE_PENALTY = -20  # flat deduction per match
UNRELATED_ROLE_KEYWORDS = [
    "mechanical engineer",
    "electrical engineer",
    "civil engineer",
    "structural engineer",
    "nurse",
    "physician",
    "construction",
    "driver",
    "warehouse",
    "manufacturing",
    "hvac",
    "plumber",
    "accountant",
    "attorney",
    "paralegal",
]

# ─── Seniority Configuration ─────────────────────────────────────────────────
SENIORITY_PENALTIES = {
    "principal": -12,
    "staff ": -10,     # trailing space avoids matching 'staffing'
    "director": -12,
    "vp ": -15,
    "vice president": -15,
    "senior staff": -12,
    "distinguished": -15,
    "head of": -12,
    "chief": -15,
    "c-level": -15,
}

SENIORITY_BOOSTS = {
    "associate": 5,
    "junior": 5,
    "jr.": 5,
    "jr ": 5,
    "early career": 6,
    "entry level": 6,
    "entry-level": 6,
    "mid-level": 3,
    "mid level": 3,
}

# ─── Core Functional Skill Weights ───────────────────────────────────────────
# These describe WHAT you do day-to-day, independent of tooling.
# Higher weight — even partial match here means the role is functionally relevant.
CORE_SKILL_WEIGHTS = {
    # Pre-sales / SE motion
    "demo": 4,
    "demos": 4,
    "proof of concept": 4,
    "poc": 4,
    "pre-sales": 5,
    "presales": 5,
    "discovery": 3,
    "solution design": 4,
    "technical presentation": 3,
    "product presentation": 3,
    "rfp": 2,
    "rfi": 2,
    # Integrations / API
    "api": 4,
    "rest": 3,
    "integration": 3,
    "integrations": 3,
    "webhook": 2,
    "data pipeline": 3,
    # Customer-facing
    "customer-facing": 4,
    "customer facing": 4,
    "enterprise client": 3,
    "stakeholder": 2,
    "client-facing": 4,
    "technical advisor": 3,
    "trusted advisor": 3,
    # Analytics / BI workflows
    "analytics": 3,
    "dashboard": 3,
    "dashboards": 3,
    "reporting": 2,
    "data visualization": 3,
    "bi": 2,
    # Data / SQL
    "sql": 4,
    "data analysis": 3,
    "data modeling": 2,
    # Implementation
    "implementation": 2,
    "onboarding": 2,
    "deployment": 2,
    # Slight negative for pure support roles
    "technical support": -2,
    "tier 1": -2,
    "tier 2": -1,
}

# ─── Tool-Specific Skill Weights ─────────────────────────────────────────────
# These are specific platforms/tools. Moderate weight — missing a tool does NOT
# disqualify a role if core functional skills are present.
TOOL_SKILL_WEIGHTS = {
    # CRM / sales tools
    "salesforce": 2,
    "hubspot": 2,
    "crm": 2,
    "salesloft": 1,
    "outreach": 1,
    # BI tools
    "tableau": 2,
    "power bi": 2,
    "looker": 2,
    "domo": 1,
    "metabase": 1,
    "sigma": 1,
    "thoughtspot": 1,
    "qlik": 1,
    # Cloud platforms
    "aws": 2,
    "gcp": 2,
    "google cloud": 2,
    "azure": 2,
    "cloud": 1,
    # Data platforms
    "snowflake": 2,
    "databricks": 2,
    "bigquery": 2,
    "redshift": 2,
    "dbt": 2,
    # Analytics / tracking
    "mixpanel": 1,
    "amplitude": 1,
    "segment": 1,
    # Integration platforms
    "mulesoft": 2,
    "workato": 2,
    "zapier": 1,
    "boomi": 2,
    "tray": 1,
    # SaaS ecosystem
    "saas": 2,
    "python": 2,
    "rest api": 3,
    "postman": 1,
    "json": 1,
    "xml": 1,
}

# ─── Transferability Map ──────────────────────────────────────────────────────
# Maps known tool-specific terms a company might use to EQUIVALENT concepts
# that Akash has experience with.
# Format: { "job_description_term": ("equivalent_concept", partial_credit_weight) }
# When the term is found in description but NOT in Akash's exact toolkit,
# the scorer awards partial_credit_weight instead of full TOOL weight.
TRANSFERABILITY_MAP = {
    # CRM equivalence (Akash knows Zoho CRM / Analytics)
    "salesforce": ("crm", 1),          # partial credit
    "dynamics 365": ("crm", 1),
    "pipedrive": ("crm", 1),
    # BI equivalence (Akash built dashboards in Zoho Analytics)
    "tableau": ("bi dashboards", 2),   # near-full credit
    "power bi": ("bi dashboards", 2),
    "looker": ("bi dashboards", 2),
    "domo": ("bi dashboards", 1),
    "metabase": ("bi dashboards", 1),
    # Cloud equivalence (general cloud experience → any platform)
    "aws": ("cloud", 1),
    "gcp": ("cloud", 1),
    "google cloud": ("cloud", 1),
    "azure": ("cloud", 1),
    # Data warehouse equivalence
    "snowflake": ("data warehouse / sql", 2),
    "redshift": ("data warehouse / sql", 2),
    "bigquery": ("data warehouse / sql", 2),
    "databricks": ("data platform", 1),
    # Integration platform equivalence
    "mulesoft": ("integration platform", 1),
    "workato": ("integration platform", 1),
    "boomi": ("integration platform", 1),
    "tray": ("integration platform", 1),
    # Python equivalence
    "r programming": ("scripting / python", 1),
    "scala": ("scripting / python", 1),
}

# ─── Ramp Feasibility Keywords ────────────────────────────────────────────────
# Jobs mentioning these words signal the company will invest in onboarding
# and growing you — critical for stretch roles.
RAMP_FEASIBILITY_KEYWORDS = [
    "training", "mentorship", "mentor", "onboarding program",
    "growth mindset", "learning environment", "learning opportunities",
    "collaborative culture", "we will teach", "will train",
    "coachable", "fast learner", "development program",
    "career development", "professional development",
    "rotational program", "associate program", "early career program",
]
RAMP_FEASIBILITY_BOOST = 4   # points added if ≥1 ramp keyword found

# ─── Hard Blocker Keywords ────────────────────────────────────────────────────
# These cause a large penalty because the role has a disqualifying requirement.
HARD_BLOCKER_PENALTY = -25
HARD_BLOCKER_KEYWORDS = [
    "security clearance",
    "secret clearance",
    "top secret",
    "ts/sci",
    "active clearance",
    "dod clearance",
    "must be a us citizen",       # combined with clearance reqs
    "must have clearance",
    "cissp required",
    "cpa required",
    "bar exam",
    "md required",
    "phd required",
    "10+ years",
    "15+ years",
    "12+ years",
]

# ─── Classification Thresholds ────────────────────────────────────────────────
# Jobs are classified into one of two labels in the daily digest.
# A job needs HIGH core score to be "High Match". Stretch = good core but tool gap.
HIGH_MATCH_CORE_THRESHOLD = 20    # core_score ≥ this → eligible for High Match
STRETCH_CORE_THRESHOLD = 10       # core_score ≥ this → eligible for Stretch
STRETCH_TOOL_CEILING = 8          # tool_score < this → label as Stretch (not High)
# High Match: core_score >= HIGH_MATCH_CORE_THRESHOLD AND tool_score >= STRETCH_TOOL_CEILING
# Stretch:    core_score >= STRETCH_CORE_THRESHOLD  AND tool_score <  STRETCH_TOOL_CEILING

# ─── Scoring Explainability ──────────────────────────────────────────────────
EXPLAIN_SCORES = True

# ─── Output Limits ───────────────────────────────────────────────────────────
MIN_JOBS_PER_RUN = 10
MAX_JOBS_PER_RUN = 15
MIN_SCORE_THRESHOLD = 5    # slightly higher now; near-match scoring is more generous
# Composition of the 10-15 daily jobs:
MAX_HIGH_MATCH = 10        # up to 10 High Match jobs
MAX_STRETCH = 5            # up to 5 Stretch but Apply jobs

# ─── Notification Schedule ───────────────────────────────────────────────────
# GitHub Actions handles scheduling; this is informational only.
SCHEDULE_HOUR_UTC = 14    # 8 AM Central Time (UTC-6 in winter / UTC-5 summer)

# ─── Company Lists by ATS ────────────────────────────────────────────────────
# Add or remove companies freely. These are companies known to hire SE/PreSales roles.

GREENHOUSE_COMPANIES = [
    "figma", "notion", "airtable", "stripe", "brex", "rippling",
    "lattice", "ramp", "gusto", "retool", "mixpanel", "amplitude",
    "segment", "cockroachdb", "dbt-labs", "fivetran", "airbyte",
    "census", "hightouch", "hex", "mode", "sigma", "thoughtspot",
    "collibra", "alation", "atlan", "monte-carlo", "anomalo",
    "clarifai", "cohere", "scale-ai", "weights-biases",
    "postman", "stoplight", "readme", "apideck",
    "salesforce", "mulesoft", "boomi", "snaplogic", "tray",
    "workato", "zapier", "celigo", "cyclr",
    "snowflake", "databricks", "starburst", "imply",
    "looker", "sisense", "domo", "qlik", "microstrategy",
    "intercom", "zendesk", "freshworks", "kustomer",
    "medallia", "qualtrics", "sprinklr",
    "hubspot", "salesloft", "outreach", "clari", "gong",
    "pendo", "fullstory", "heap", "logrocket",
    "samsara", "fleetio", "platform-science",
    "cloudflare", "fastly", "akamai-technologies",
    "hashicorp", "pulumi", "env0", "spacelift",
    "grafana", "datadog", "newrelic", "dynatrace", "honeycomb",
    "lacework", "orca-security", "wiz", "snyk", "veracode",
]

LEVER_COMPANIES = [
    "scale-ai", "census", "hightouch", "metabase", "preset",
    "fivetran", "stitch", "talend", "informatica", "matillion",
    "dbt-labs", "transform", "lightdash", "cube",
    "alloy-automation", "workato", "tray-io", "parabola",
    "segment", "rudderstack", "mparticle",
    "chartio", "klipfolio", "geckoboard",
    "gainsight", "totango", "churnzero", "clientsuccess",
    "jira-align", "planview", "targetprocess",
    "miro", "lucidchart", "creatio",
    "outreach", "salesloft", "groove", "yesware",
    "zuora", "chargebee", "maxio", "recurly",
    "chargify", "paddle", "fastspring",
    "cloudinary", "imgix", "uploadcare",
    "auth0", "okta", "onelogin", "ping-identity",
    "crowdstrike", "sentinelone", "darktrace",
    "algolia", "elasticsearch", "coveo",
    "contentful", "sanity", "storyblok", "prismic",
    "netlify", "vercel", "render", "railway",
    "lob", "smarty-streets", "stannp",
    "twilio", "bandwidth", "vonage", "sinch",
]

ASHBY_COMPANIES = [
    "ashby", "ramp", "brex", "mercury", "column-tax",
    "watershed", "pachama", "terraformation",
    "drata", "vanta", "secureframe", "laika",
    "persona", "sardine", "unit21", "sift",
    "modern-treasury", "increase", "column",
    "benchling", "synthego", "ginkgo-bioworks",
    "scale-ai", "cohere", "adept", "inflection",
    "robinhood", "coinbase", "gemini", "kraken",
    "instabase", "ironclad", "spotdraft", "leigalaw",
    "mural", "stormboard", "klaxoon",
    "productboard", "coda", "craft", "fibery",
    "linear", "height", "plane",
    "loom", "mmhmm", "descript",
    "deel", "remote", "papaya-global", "oyster",
]

WORKABLE_COMPANIES = [
    "workable", "bamboohr", "namely", "hibob", "personio",
    "lattice", "culture-amp", "leapsome", "betterworks",
    "mimecast", "proofpoint", "barracuda",
    "freshdesk", "kayako", "helpscout", "groove",
    "mailchimp", "klaviyo", "attentive", "sms-magic",
    "semrush", "moz", "ahrefs", "majestic",
    "hotjar", "crazy-egg", "mouseflow", "contentsquare",
    "podium", "birdeye", "reputation", "grade-us",
    "brightcove", "vidyard", "wistia", "vimeo",
    "docusign", "hellosign", "pandadoc", "proposify",
    "boldsign", "signnow", "signwell",
    "xero", "freshbooks", "wave", "kashoo",
    "coupa", "tipalti", "bill", "airbase",
    "brainware", "esker", "readsoft", "kofax",
]
