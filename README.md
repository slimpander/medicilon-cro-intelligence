# CRO US Market Intelligence — Medicilon Gap Analysis

A self-contained interactive competitive intelligence map for Medicilon's US market strategy.

## Quick Start

```bash
# 1. Serve locally (required for fetch to work)
python -m http.server 8000

# 2. Open in browser
# http://localhost:8000
```

## Files

| File | Purpose |
|---|---|
| `index.html` | Self-contained interactive report (D3 + TopoJSON) |
| `data/cro_data.json` | CRO data (pre-populated with curated data) |
| `scraper.py` | Python scraper to refresh data |

## Running the Scraper

```bash
pip install requests beautifulsoup4

# Use curated data only (fast, no network):
python scraper.py --no-scrape

# Attempt live scraping + curated fallback:
python scraper.py

# Custom output path:
python scraper.py --output data/cro_data.json
```

After running, click **Refresh Data** in the sidebar to reload the map.

## Features

- **Interactive US choropleth map** — CRO density by state (light → dark = fewer → more CROs)
- **Service area filters** — filter by DMPK, ADME, Tox, In Vivo, CMC, Bioanalysis, etc.
- **Medicilon core services preset** — one-click filter to Medicilon's service portfolio
- **Hover tooltips** — see all CROs in a state at a glance
- **Click-to-detail panel** — full CRO list, services, gap analysis, and opportunity score
- **Top Opportunities tab** — ranked states for Medicilon entry with reasoning
- **Service Whitespace tab** — which services are least covered nationally
- **Underserved States tab** — states with <2 CROs covering Medicilon's core services

## Opportunity Scoring

Each state gets a 0–100 score based on:

```
score = (biotech_hub_weight × 3) + service_gap_score + no_presence_bonus
```

- **Biotech hub weight**: MA/CA = 10, NJ = 9, NC/TX = 8, PA/NY = 7 …
- **Service gap score**: +10 per uncovered service, +5 per single-provider service, +2 per 2-provider service
- **No presence bonus**: +15 if Medicilon has no current US office in that state

## CROs Included

Charles River, Covance/Labcorp, WuXi AppTec, Eurofins, Pharmaron, Crown Bioscience, Syneos Health, ICON plc, BioAgilytix, Altasciences, Celerion, Biotrial, **Medicilon**

## Tech Stack

- D3.js v7 (CDN)
- TopoJSON v3 (CDN)
- US Atlas states-10m.json (CDN)
- Pure HTML/CSS/JS — no build step
- Google Fonts Inter
