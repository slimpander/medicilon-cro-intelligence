# Medicilon CRO Intelligence Platform

Full-stack BD intelligence tool for Medicilon's US market strategy.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
python run.py

# 3. Open in browser
# http://localhost:8000

# Login: admin / admin123  (change password in Settings after first login)
```

## Architecture

```
cro-platform/
├── backend/
│   ├── main.py              # FastAPI server — all API routes
│   ├── scheduler.py         # Cron runner for digests + aggregation
│   └── services/
│       ├── funding_fetcher.py       # ClinicalTrials.gov + SEC EDGAR + NIH
│       ├── crunchbase_client.py     # Crunchbase API (optional key)
│       ├── linkedin_aggregator.py   # BD signals from news RSS (no account needed)
│       ├── linkedin_monitor.py      # Chrome extension data processor
│       ├── news_fetcher.py          # RSS news aggregation
│       ├── lead_scorer.py           # Multi-dimensional AI lead scoring
│       ├── notification_pipeline.py # Email digests + desktop alerts
│       ├── patent_search.py         # Google Patents scraper
│       └── abbreviation_engine.py  # Biopharma abbreviation expansion
├── frontend/
│   ├── index.html           # App shell + navigation
│   ├── css/style.css        # Theme + components
│   ├── js/
│   │   ├── app.js           # Router, auth, data loader, utilities
│   │   └── pages/           # One module per page
│   └── data/                # Static JSON (refreshed by backend scripts)
├── linkedin-extension/      # Chrome extension for LinkedIn data
├── data/platform.db         # SQLite (auto-created, gitignored)
├── run.py                   # Server launcher
└── start.bat                # Windows double-click launcher
```

## Pages

| Page | Route | Description |
|---|---|---|
| Dashboard | `#dashboard` | BD Command Center — News, Patents, LinkedIn, Funding |
| BD Intel Feed | `#linkedin` | Automated signal detection from public sources |
| Deals & M&A | `#pitchbook` | Recent biotech deals from RSS feeds |
| Funding Intel | `#crunchbase` | Crunchbase company search (requires API key) |
| News Feed | `#news` | CRO/biotech news aggregation |
| Market Map | `#map` | US CRO competitive coverage map |
| Lead Intelligence | `#leads` | Scored BD leads from ClinicalTrials + SEC + NIH |
| CRO Profiles | `#cros` | Competitor analysis + service coverage matrix |
| Settings | `#settings` | API keys, notifications, data management |

## API Keys (Optional)

Configure in **Settings** page after login:

| Service | Where to get | What it enables |
|---|---|---|
| Crunchbase | [data.crunchbase.com](https://data.crunchbase.com/docs) | Rich company profiles, funding rounds, investor data |
| NewsAPI | [newsapi.org/register](https://newsapi.org/register) | Additional news articles |

Without API keys, the platform uses free public sources: SEC EDGAR, ClinicalTrials.gov, NIH RePORTER, FierceBiotech RSS, Google Patents.

## Data Refresh

```bash
# Manual refresh (from project root)
python run.py  # Start server, then use Settings → "Run Now" button

# Or via scheduler
python backend/scheduler.py aggregate       # BD intelligence scan
python backend/scheduler.py morning         # Morning email digest
python backend/scheduler.py generate-alerts # Create alert notifications
```

## Chrome Extension (Optional)

Enhances the BD Intel Feed with direct LinkedIn post data:

1. Open Chrome → Extensions → "Load unpacked"
2. Select the `linkedin-extension/` folder
3. Go to LinkedIn, click the extension icon to start monitoring
4. Posts are sent to `POST /api/linkedin/posts` and scored automatically

## Security Notes

- Change the default admin password after first login (Settings → change password)
- The platform is designed for local/intranet use — do not expose to the public internet without adding HTTPS + proper auth
- `data/platform.db` contains user passwords (bcrypt hashed) — keep it out of version control (already in .gitignore)
