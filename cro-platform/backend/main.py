"""
Medicilon CRO Intelligence Platform — Backend Server
FastAPI-based: auth, Crunchbase integration, LinkedIn agent, notifications, settings
"""

import json
import os
import sqlite3
import hashlib
import secrets
import bcrypt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── App Setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Medicilon CRO Intelligence API",
    version="0.3.0",
    description="Backend for Medicilon market intelligence platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = BASE_DIR / "data" / "platform.db"


# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'bd',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY,
            crunchbase_key TEXT,
            pitchbook_email TEXT,
            linkedin_email TEXT,
            linkedin_session TEXT,
            newsapi_key TEXT,
            notif_email TEXT,
            notif_morning INTEGER DEFAULT 1,
            notif_afternoon INTEGER DEFAULT 0,
            notif_evening INTEGER DEFAULT 0,
            desktop_notif INTEGER DEFAULT 1,
            min_lead_score INTEGER DEFAULT 70,
            alert_frequency TEXT DEFAULT 'daily',
            refresh_interval INTEGER DEFAULT 43200,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            link_page TEXT DEFAULT 'leads',
            lead_source_id TEXT,
            read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS linkedin_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT UNIQUE,
            post_url TEXT,
            author_name TEXT,
            author_title TEXT,
            author_company TEXT,
            content TEXT,
            post_date TEXT,
            relevance_score REAL DEFAULT 0,
            matched_keywords TEXT,
            processed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS linkedin_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT UNIQUE,
            name TEXT NOT NULL,
            title TEXT,
            company TEXT,
            company_state TEXT,
            linkedin_url TEXT,
            connection_degree TEXT,
            relevance_score REAL DEFAULT 0,
            lead_source_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()

    # Create default admin user if none exist
    cursor = conn.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)",
            ("admin", pw_hash, "admin@medicilon.com", "admin")
        )
        conn.commit()
        print(f"[INIT] Created default admin user (admin / admin123) — change password in Settings")

    conn.close()


# ── Models ────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class SettingsUpdate(BaseModel):
    crunchbase_key: Optional[str] = None
    pitchbook_email: Optional[str] = None
    linkedin_email: Optional[str] = None
    linkedin_session: Optional[str] = None
    newsapi_key: Optional[str] = None
    notif_email: Optional[str] = None
    notif_morning: Optional[bool] = None
    notif_afternoon: Optional[bool] = None
    notif_evening: Optional[bool] = None
    desktop_notif: Optional[bool] = None
    min_lead_score: Optional[int] = None
    alert_frequency: Optional[str] = None
    refresh_interval: Optional[int] = None


class NotificationCreate(BaseModel):
    message: str
    link_page: str = "leads"
    lead_source_id: Optional[str] = None


# ── Auth Helpers ──────────────────────────────────────────────────────────────
SESSIONS = {}  # In-memory session store (upgrade to Redis for production)


def get_current_user(request: Request) -> dict:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token or token not in SESSIONS:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = SESSIONS[token]
    if datetime.fromisoformat(session["expires"]) < datetime.now():
        del SESSIONS[token]
        raise HTTPException(status_code=401, detail="Session expired")
    return session["user"]


# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
def login(body: LoginRequest):
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, email, role, password_hash FROM users WHERE username = ?",
        (body.username,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_hex(32)
    user = {"id": row["id"], "username": row["username"], "email": row["email"], "role": row["role"]}
    SESSIONS[token] = {
        "user": user,
        "expires": (datetime.now() + timedelta(hours=24)).isoformat(),
    }

    return {"token": token, "user": user}


@app.post("/api/auth/logout")
def logout(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    SESSIONS.pop(token, None)
    return {"ok": True}


@app.post("/api/auth/register")
def register(body: LoginRequest):
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (body.username,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="Username already exists")
    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (body.username, pw_hash))
    conn.commit()
    conn.close()
    return {"ok": True, "message": "User created. Login to get a token."}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

@app.post("/api/auth/change-password")
def change_password(body: PasswordChange, user=Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
    if not row or not bcrypt.checkpw(body.current_password.encode(), row["password_hash"].encode()):
        conn.close()
        raise HTTPException(status_code=401, detail="Current password incorrect")
    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
    conn.commit()
    conn.close()
    return {"ok": True, "message": "Password updated"}


# ── Settings Routes ───────────────────────────────────────────────────────────
@app.get("/api/settings")
def get_settings(user=Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT * FROM settings WHERE user_id = ?", (user["id"],)).fetchone()
    conn.close()

    if not row:
        # Return defaults
        return {
            "crunchbase_key": None,
            "newsapi_key": None,
            "notif_email": user.get("email", ""),
            "notif_morning": True,
            "notif_afternoon": False,
            "notif_evening": False,
            "desktop_notif": True,
            "min_lead_score": 70,
            "alert_frequency": "daily",
            "refresh_interval": 43200,
        }

    return dict(row)


@app.put("/api/settings")
def update_settings(body: SettingsUpdate, user=Depends(get_current_user)):
    conn = get_db()

    # Upsert settings
    fields = []
    values = []
    for k, v in body.dict(exclude_none=True).items():
        fields.append(f"{k} = ?")
        values.append(v)

    if fields:
        values.append(user["id"])
        sql = f"""
            INSERT INTO settings (user_id, {', '.join(body.dict(exclude_none=True).keys())})
            VALUES (?, {', '.join(['?'] * len(body.dict(exclude_none=True)))})
            ON CONFLICT(user_id) DO UPDATE SET {' '.join(fields)}
        """
        conn.execute(sql, [user["id"]] + list(body.dict(exclude_none=True).values()))
        conn.commit()

    conn.close()
    return {"ok": True}


# ── Crunchbase Routes ─────────────────────────────────────────────────────────
from services.pitchbook_intel import get_recent_deals as pitchbook_deals, search_deals as pitchbook_search


@app.get("/api/pitchbook/deals")
async def get_pitchbook_deals(limit: int = 8, deal_type: str = "", live: bool = True):
    """Get recent biotech/CRO deals. Tries live RSS scrape first, falls back to curated data."""
    # Priority 1: Try live scraped deals
    if live:
        try:
            deals_path = BASE_DIR / "frontend" / "data" / "deals.json"
            if deals_path.exists():
                import json as _json
                with open(deals_path, "r", encoding="utf-8") as f:
                    scraped = _json.load(f)
                scraped_deals = scraped.get("deals", [])
                if scraped_deals:
                    if deal_type:
                        scraped_deals = [d for d in scraped_deals if d.get("deal_type", "").lower() == deal_type.lower()]
                    return {
                        "deals": scraped_deals[:limit],
                        "total": len(scraped_deals[:limit]),
                        "generated_at": scraped.get("metadata", {}).get("generated", datetime.now().isoformat()),
                        "source": "Live RSS (FierceBiotech, Endpoints, BioPharma Dive)",
                    }
        except Exception:
            pass

    # Priority 2: Fall back to curated PitchBook-style data
    if deal_type:
        result = pitchbook_search(deal_type=deal_type, limit=limit)
    else:
        result = pitchbook_deals(limit=limit)
    return result
@app.get("/api/crunchbase/test")
async def test_crunchbase(key: str, user=Depends(get_current_user)):
    """Test a Crunchbase API key"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.crunchbase.com/api/v4/searches/organizations",
                params={"user_key": key, "limit": 1},
            )
            if r.status_code == 200:
                data = r.json()
                return {"ok": True, "company_count": data.get("count", 0)}
            else:
                return {"ok": False, "error": f"API returned {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/crunchbase/search")
async def search_crunchbase(
    keyword: str = "",
    state: str = "",
    funding_stage: str = "",
    limit: int = 20,
    user=Depends(get_current_user),
):
    """Search Crunchbase for biotech companies."""
    conn = get_db()
    row = conn.execute("SELECT crunchbase_key FROM settings WHERE user_id = ?", (user["id"],)).fetchone()
    conn.close()
    if not row or not row["crunchbase_key"]:
        raise HTTPException(status_code=400, detail="Crunchbase API key not configured. Add it in Settings.")
    try:
        from services.crunchbase_client import CrunchbaseClient
        client = CrunchbaseClient(api_key=row["crunchbase_key"])
        locations = None
        if state:
            state_map = {"MA":"Massachusetts","CA":"California","NJ":"New Jersey","NC":"North Carolina","TX":"Texas","PA":"Pennsylvania","NY":"New York","MD":"Maryland","IL":"Illinois","WA":"Washington","CO":"Colorado","FL":"Florida","GA":"Georgia","VA":"Virginia","MN":"Minnesota"}
            locations = [state_map.get(state, state)]
        companies = client.search_companies(keyword=keyword, locations=locations, funding_stage=funding_stage, limit=limit)
        return {"ok":True,"count":len(companies),"companies":[{"name":c.name,"permalink":c.permalink,"description":c.description[:150] if c.description else "","state":c.state,"city":c.city,"funding_stage":c.funding_stage,"total_funding":c.total_funding_usd,"total_funding_display":_fmt_usd2(c.total_funding_usd),"website":c.website,"founded":c.founded_on} for c in companies]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/crunchbase/company/{permalink}")
async def get_crunchbase_company(permalink: str, user=Depends(get_current_user)):
    """Get detailed Crunchbase info for a company."""
    conn = get_db()
    row = conn.execute("SELECT crunchbase_key FROM settings WHERE user_id = ?", (user["id"],)).fetchone()
    conn.close()
    if not row or not row["crunchbase_key"]:
        raise HTTPException(status_code=400, detail="Crunchbase API key not configured.")
    try:
        from services.crunchbase_client import CrunchbaseClient
        client = CrunchbaseClient(api_key=row["crunchbase_key"])
        company = client.get_organization(permalink)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        rounds = client.get_funding_rounds(permalink, limit=10)
        return {"ok":True,"company":{"name":company.name,"description":company.description,"state":company.state,"city":company.city,"website":company.website,"linkedin":company.linkedin_url,"founded":company.founded_on,"funding_stage":company.funding_stage,"total_funding":company.total_funding_usd,"total_funding_display":_fmt_usd2(company.total_funding_usd),"employees":company.num_employees,"categories":company.categories[:10]},"funding_rounds":[{"type":r.funding_type,"date":r.announced_on,"amount":r.money_raised_usd,"amount_display":r.money_raised,"investors":r.lead_investors,"num_investors":r.num_investors} for r in rounds]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/crunchbase/recently-funded")
async def get_recently_funded(days: int = 90, state: str = "", limit: int = 20, user=Depends(get_current_user)):
    """Get recently funded biotech companies."""
    conn = get_db()
    row = conn.execute("SELECT crunchbase_key FROM settings WHERE user_id = ?", (user["id"],)).fetchone()
    conn.close()
    if not row or not row["crunchbase_key"]:
        raise HTTPException(status_code=400, detail="Crunchbase API key not configured.")
    try:
        from services.crunchbase_client import CrunchbaseClient
        client = CrunchbaseClient(api_key=row["crunchbase_key"])
        leads = client.discover_recently_funded(days_back=days, states=[state] if state else None, limit=limit)
        return {"ok": True, "count": len(leads), "leads": leads, "source": "crunchbase"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/funding/companies")
async def get_funding_companies(days: int = 120, state: str = "", limit: int = 30):
    """Get recently funded biotech companies — Crunchbase if available, otherwise SEC EDGAR + news.
    Public endpoint. Automatically upgrades data quality when Crunchbase key is configured."""
    import sqlite3 as _sql
    conn = _sql.connect(str(DB_PATH))
    conn.row_factory = _sql.Row
    # Try to find any user's crunchbase key (first configured one)
    row = conn.execute("SELECT crunchbase_key FROM settings WHERE crunchbase_key IS NOT NULL AND crunchbase_key != '' LIMIT 1").fetchone()
    conn.close()

    crunchbase_key = row["crunchbase_key"] if row else None
    source = "sec_edgar"
    leads = []

    if crunchbase_key:
        # ── CRUNCHBASE MODE: rich, accurate data ──────────────────────────
        try:
            from services.crunchbase_client import CrunchbaseClient
            client = CrunchbaseClient(api_key=crunchbase_key)
            states_list = [state] if state else None
            cb_leads = client.discover_recently_funded(days_back=days, states=states_list, limit=limit)
            # Normalize to unified format
            for l in cb_leads:
                leads.append({
                    "name": l.get("name") or l.get("company_name", ""),
                    "state": l.get("state", ""),
                    "stage": l.get("funding_stage") or l.get("last_funding_type", "Funding"),
                    "focus": (l.get("description") or l.get("short_description", ""))[:120],
                    "total_funding_display": _fmt_usd(l.get("total_funding_usd") or l.get("funding_total", {}).get("value_usd", 0)),
                    "total_funding_usd": l.get("total_funding_usd") or l.get("funding_total", {}).get("value_usd", 0),
                    "last_round_amount": _fmt_usd(l.get("last_funding_total") or l.get("last_equity_funding_total")),
                    "last_round_date": l.get("last_funding_at") or l.get("last_equity_funding_at", ""),
                    "investors": l.get("investor_names") or l.get("lead_investors", ""),
                    "url": l.get("cb_url") or f"https://crunchbase.com/organization/{l.get('permalink','')}",
                    "needs": _infer_services((l.get("description") or "") + " " + ", ".join(l.get("categories") or [])),
                    "source": "Crunchbase",
                    "source_quality": "high",
                })
            source = "crunchbase"
        except Exception as e:
            print(f"[Funding] Crunchbase failed ({e}), falling back to SEC EDGAR")
            crunchbase_key = None  # Force fallback

    if not crunchbase_key:
        # ── SEC EDGAR + NEWS MODE: good data, no API key needed ──────────
        from services.funding_fetcher import fetch_sec_funding, fetch_clinical_trials, deduplicate
        raw = []
        raw += fetch_sec_funding(lookback_days=days)
        raw += fetch_clinical_trials(lookback_days=days)
        raw = deduplicate(raw)
        # Also merge any news-scraped deals
        try:
            deals_path = BASE_DIR / "frontend" / "data" / "deals.json"
            if deals_path.exists():
                import json as _json
                with open(deals_path, "r", encoding="utf-8") as f:
                    deals_data = _json.load(f)
                for d in deals_data.get("deals", []):
                    if d.get("amount_usd"):
                        raw.append({
                            "name": d.get("target", ""),
                            "state": "",
                            "stage": d.get("deal_type", "Funding"),
                            "focus": d.get("description", "")[:120],
                            "total_funding_display": d.get("amount", ""),
                            "total_funding_usd": d.get("amount_usd", 0),
                            "last_round_date": d.get("date", ""),
                            "investors": "",
                            "url": d.get("url", ""),
                            "needs": _infer_services(d.get("description", "")),
                            "source": d.get("source", "News RSS"),
                            "source_quality": "medium",
                        })
        except Exception:
            pass

        # Dedup and limit — only include entries with funding amounts
        seen = set()
        deduped = []
        for l in raw:
            name = (l.get("name") or "").lower().strip()
            amt = l.get("total_funding_usd", 0) or 0
            # Skip entries without actual funding amounts
            if not name or amt <= 0:
                continue
            if name in seen:
                continue
            seen.add(name)
            deduped.append({
                    "name": l.get("name", ""),
                    "state": l.get("state", ""),
                    "stage": l.get("stage", "Funding"),
                    "focus": l.get("focus", "")[:120],
                    "total_funding_display": l.get("total_funding_display") or _fmt_usd(amt),
                    "total_funding_usd": amt,
                    "last_round_date": l.get("last_round_date") or l.get("date", ""),
                    "investors": l.get("investors", ""),
                    "url": l.get("url", ""),
                    "needs": l.get("needs", []),
                    "source": l.get("source", "SEC EDGAR"),
                    "source_quality": l.get("source_quality", "medium"),
                })
        deduped.sort(key=lambda x: x["total_funding_usd"] or 0, reverse=True)
        leads = deduped[:limit]
        source = "sec_edgar"

    return {
        "ok": True,
        "count": len(leads),
        "source": source,
        "crunchbase_enabled": bool(crunchbase_key),
        "leads": leads,
    }


def _fmt_usd2(amount):
    if not amount: return ""
    if amount >= 1_000_000_000: return f"${amount/1e9:.1f}B"
    if amount >= 1_000_000: return f"${amount/1e6:.0f}M"
    if amount >= 1_000: return f"${amount/1e3:.0f}K"
    return f"${amount}"

_fmt_usd = _fmt_usd2  # alias


def _infer_services(text: str):
    """Infer needed CRO services from company description."""
    ta_map = {
        "oncology": ["In Vivo / Mouse Services", "Bioanalysis", "DMPK"],
        "cancer": ["In Vivo / Mouse Services", "Bioanalysis", "DMPK"],
        "rare disease": ["Toxicology", "Bioanalysis"],
        "cns": ["DMPK", "Bioanalysis", "In Vivo / Mouse Services"],
        "neurology": ["DMPK", "Bioanalysis"],
        "immunology": ["Bioanalysis", "Protein Sciences / Biologics"],
        "autoimmune": ["Bioanalysis", "Toxicology"],
        "infectious": ["DMPK", "ADME", "Toxicology"],
        "cardiovascular": ["DMPK", "ADME", "In Vivo / Mouse Services"],
        "metabolic": ["ADME", "DMPK"],
        "biologics": ["Protein Sciences / Biologics", "Bioanalysis"],
        "antibody": ["Protein Sciences / Biologics", "Bioanalysis"],
        "gene therapy": ["Toxicology", "Bioanalysis"],
        "cell therapy": ["Bioanalysis", "In Vivo / Mouse Services"],
        "adc": ["Bioanalysis", "DMPK", "CMC"],
        "rna": ["DMPK", "Toxicology", "CMC"],
        "small molecule": ["DMPK", "ADME", "Toxicology"],
        "peptide": ["DMPK", "CMC", "Bioanalysis"],
    }
    text_lower = (text or "").lower()
    services = set()
    for kw, svcs in ta_map.items():
        if kw in text_lower:
            services.update(svcs)
    return sorted(services) or ["DMPK", "Bioanalysis"]


# ── Notification Routes ───────────────────────────────────────────────────────
from services.notification_pipeline import pipeline as notif_pipeline


@app.get("/api/notifications")
def get_notifications(user=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (user["id"],)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/notifications")
def create_notification(body: NotificationCreate, user=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO notifications (user_id, message, link_page, lead_source_id) VALUES (?, ?, ?, ?)",
        (user["id"], body.message, body.link_page, body.lead_source_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.put("/api/notifications/{notif_id}/read")
def mark_read(notif_id: int, user=Depends(get_current_user)):
    conn = get_db()
    conn.execute("UPDATE notifications SET read = 1 WHERE id = ? AND user_id = ?", (notif_id, user["id"]))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/notifications/digest")
async def send_digest(
    email: str = "",
    period: str = "daily",
    user=Depends(get_current_user),
):
    """Send an email digest."""
    to_email = email or user.get("email", "")
    if not to_email:
        raise HTTPException(status_code=400, detail="No email configured. Add in Settings.")
    result = notif_pipeline.send_email_digest(to_email=to_email, user_id=user["id"], period=period)
    return result


@app.post("/api/notifications/generate-alerts")
async def generate_alerts(user=Depends(get_current_user)):
    """Generate alert notifications based on current data."""
    result = notif_pipeline.generate_daily_alerts()
    return {"ok": True, **result}


@app.get("/api/notifications/desktop-push")
def get_desktop_notifications(user=Depends(get_current_user)):
    """Get pending desktop notifications for the frontend."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE user_id = ? AND read = 0 ORDER BY created_at DESC LIMIT 10",
        (user["id"],)
    ).fetchall()
    conn.close()
    return [
        notif_pipeline.generate_desktop_notification({
            "message": r["message"],
            "link_page": r["link_page"],
            "lead_source_id": r["lead_source_id"],
        })
        for r in rows
    ]


@app.post("/api/admin/run-digest")
async def admin_run_digest(period: str = "daily", user=Depends(get_current_user)):
    """Admin: manually trigger a digest run for all users."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    result = notif_pipeline._run_period_digest(period)
    return {"ok": True, **result}


# ── Data Refresh Routes ───────────────────────────────────────────────────────
@app.post("/api/refresh/intelligence")
async def refresh_intelligence(user=Depends(get_current_user)):
    """Trigger intelligence data refresh — uses internal funding_fetcher service."""
    from services.funding_fetcher import (
        fetch_clinical_trials, fetch_sec_funding, fetch_nih_grants,
        deduplicate, enrich_and_score, save,
    )
    conn = get_db()
    row = conn.execute("SELECT crunchbase_key FROM settings WHERE user_id = ?", (user["id"],)).fetchone()
    conn.close()

    all_leads = []
    all_leads += fetch_clinical_trials(90)
    all_leads += fetch_sec_funding(90)
    all_leads += fetch_nih_grants(90)

    # Optional: Crunchbase if key is configured
    if row and row["crunchbase_key"]:
        try:
            from services.funding_fetcher import fetch_crunchbase
            cb_leads = fetch_crunchbase(row["crunchbase_key"], lookback_days=90)
            all_leads += cb_leads
        except Exception as e:
            print(f"[Refresh] Crunchbase skipped: {e}")

    all_leads = deduplicate(all_leads)
    all_leads = enrich_and_score(all_leads)
    save(all_leads, 90, bool(row and row["crunchbase_key"]))

    by_source = {}
    for l in all_leads:
        by_source[l["source"]] = by_source.get(l["source"], 0) + 1

    return {
        "ok": True,
        "total_leads": len(all_leads),
        "sources": by_source,
        "top_states": list(set(l["state"] for l in all_leads if l.get("state") != "US"))[:10],
    }


@app.post("/api/refresh/news")
async def refresh_news(user=Depends(get_current_user)):
    """Trigger news data refresh — uses internal news_fetcher service (RSS feeds)."""
    from services.news_fetcher import fetch_all_news, save_news
    try:
        articles = fetch_all_news(use_gdelt=False)
        result = save_news(articles)
        return {"ok": True, "count": result["count"], "source": "RSS feeds (FierceBiotech, Endpoints, BioPharma Dive, Google News)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/refresh/deals")
async def refresh_deals(user=Depends(get_current_user)):
    """Trigger biotech deals refresh from RSS news sources."""
    from services.news_fetcher import fetch_biotech_deals, save_deals
    try:
        deals = fetch_biotech_deals(limit=20)
        result = save_deals(deals)
        return {"ok": True, "count": result["count"], "source": "FierceBiotech, Endpoints, BioPharma Dive"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── LinkedIn Routes (Phase 3.4) ──────────────────────────────────────────────
# LinkedIn monitor singleton
from services.linkedin_monitor import monitor as linkedin_monitor


logger = None  # will be set in startup


@app.get("/api/linkedin/posts")
def get_linkedin_posts(limit: int = 20, min_score: float = 0):
    """Get scored LinkedIn posts from the database. Public read."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM linkedin_posts WHERE relevance_score >= ? ORDER BY relevance_score DESC LIMIT ?",
        (min_score, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/linkedin/posts/high-priority")
def get_high_priority_posts():
    """Get only high-priority posts (score >= 70). Public read."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM linkedin_posts WHERE relevance_score >= 70 ORDER BY relevance_score DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/linkedin/contacts")
def get_linkedin_contacts(company: Optional[str] = None):
    """Get discovered LinkedIn contacts. Public read."""
    conn = get_db()
    if company:
        rows = conn.execute(
            "SELECT * FROM linkedin_contacts WHERE company LIKE ? ORDER BY relevance_score DESC",
            (f"%{company}%",)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM linkedin_contacts ORDER BY relevance_score DESC LIMIT 50"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/linkedin/posts")
async def submit_linkedin_post(post: dict, request: Request):
    """Receive a post from the Chrome extension, score it, and store it."""
    try:
        scored = linkedin_monitor.score_post(post)
        enriched = {**post, **scored}
        linkedin_monitor.store_post(enriched)

        # Store contact if found
        if scored.get("contact"):
            linkedin_monitor.store_contact(scored["contact"])

        return {
            "ok": True,
            "relevance_score": scored["relevance_score"],
            "matched_keywords": scored["matched_keywords"],
            "is_high_priority": scored["is_high_priority"],
            "bd_notes": scored["bd_notes"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/linkedin/posts/batch")
async def submit_linkedin_batch(payload: dict, request: Request):
    """Process a batch of LinkedIn posts from the extension."""
    posts = payload.get("posts", [])
    if not posts:
        raise HTTPException(status_code=400, detail="No posts provided")

    try:
        result = linkedin_monitor.process_post_batch(posts)

        # Store all
        for p in result["all_results"]:
            linkedin_monitor.store_post(p)
            if p.get("contact"):
                linkedin_monitor.store_contact(p["contact"])

        return {
            "ok": True,
            "posts_processed": result["posts_processed"],
            "high_priority_count": result["high_priority_count"],
            "contacts_found": result["contacts_found"],
            "high_priority": [
                {
                    "author": p.get("author"),
                    "score": p.get("relevance_score"),
                    "keywords": p.get("matched_keywords"),
                    "bd_notes": p.get("bd_notes"),
                }
                for p in result["high_priority"]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/linkedin/report")
def get_linkedin_report():
    """Get weekly LinkedIn monitoring report. Public read."""
    return linkedin_monitor.get_weekly_report()


@app.get("/api/linkedin/recommendations")
def get_linkedin_recommendations():
    """Generate AI-powered potential client recommendations from LinkedIn data.
    Analyzes matched posts, decision-maker contacts, and company signals to
    identify the most promising BD targets."""
    conn = get_db()

    # Get top-scoring posts with decision-maker contacts
    posts = conn.execute(
        """SELECT p.*, c.name as contact_name, c.title as contact_title
           FROM linkedin_posts p
           LEFT JOIN linkedin_contacts c ON c.company = p.author_company
           WHERE p.relevance_score >= 20
           ORDER BY p.relevance_score DESC LIMIT 20"""
    ).fetchall()
    conn.close()

    if not posts:
        return {"recommendations": [], "note": "No LinkedIn posts yet. Connect the Chrome extension to start monitoring."}

    recommendations = []
    seen_companies = set()

    for post in posts:
        company = (post["author_company"] or "").strip()
        if not company or company in seen_companies:
            continue
        seen_companies.add(company)

        # Calculate recommendation score
        relevance = post["relevance_score"] or 0
        keywords = (post["matched_keywords"] or "").split(",")
        has_dm = bool(post["contact_name"])

        # Score boost for decision-maker presence
        rec_score = min(100, relevance + (15 if has_dm else 0))

        # Generate recommendation reason
        signals = [k.strip() for k in keywords if k.strip()]
        reason_parts = []
        if "outsourcing" in (post["content"] or "").lower() or any("CRO" in k or "outsourc" in k for k in signals):
            reason_parts.append("Active CRO outsourcing signal detected")
        elif has_dm:
            reason_parts.append(f"Decision-maker ({post['contact_title'] or 'senior leader'}) engaged")
        elif len(signals) >= 3:
            reason_parts.append(f"Strong signal match on {len(signals)} relevant keywords")
        else:
            reason_parts.append("Aligned with Medicilon service areas")

        reason = ". ".join(reason_parts) + "." if reason_parts else ""

        recommendations.append({
            "company": company,
            "contact_name": post["contact_name"],
            "contact_title": post["contact_title"],
            "match_score": round(rec_score, 1),
            "signals": signals[:5],
            "reason": reason,
            "source": "LinkedIn post analysis",
        })

        if len(recommendations) >= 6:
            break

    return {
        "recommendations": recommendations,
        "total_analyzed": len(seen_companies),
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/api/linkedin/stats")
def get_linkedin_stats():
    """Get LinkedIn monitoring statistics. Public read."""
    conn = get_db()
    total_posts = conn.execute("SELECT COUNT(*) FROM linkedin_posts").fetchone()[0]
    total_contacts = conn.execute("SELECT COUNT(*) FROM linkedin_contacts").fetchone()[0]
    avg_score_row = conn.execute("SELECT AVG(relevance_score) FROM linkedin_posts WHERE relevance_score > 0").fetchone()
    high_priority = conn.execute("SELECT COUNT(*) FROM linkedin_posts WHERE relevance_score >= 70").fetchone()[0]
    conn.close()
    return {
        "total_posts": total_posts,
        "total_contacts": total_contacts,
        "avg_relevance": round(avg_score_row[0] or 0, 1),
        "high_priority": high_priority,
    }


@app.post("/api/linkedin/search")
async def search_linkedin(
    keywords: str = "",
    company: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Search stored LinkedIn posts by keywords (local search)."""
    conn = get_db()
    query = "SELECT * FROM linkedin_posts WHERE 1=1"
    params = []
    if keywords:
        for kw in keywords.split(","):
            kw = kw.strip()
            if kw:
                query += " AND (content LIKE ? OR matched_keywords LIKE ?)"
                params.extend([f"%{kw}%", f"%{kw}%"])
    if company:
        query += " AND author_company LIKE ?"
        params.append(f"%{company}%")
    query += " ORDER BY relevance_score DESC LIMIT 30"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {
        "ok": True,
        "count": len(rows),
        "results": [dict(r) for r in rows],
    }


# ── LinkedIn Aggregator — No Browser Needed ──────────────────────────────────
@app.post("/api/linkedin/aggregate")
async def aggregate_linkedin_intelligence(user=Depends(get_current_user)):
    """Run multi-source intelligence aggregation — NO LinkedIn account/browser needed.
    Pulls BD signals from Google News, FierceBiotech, Endpoints, BioPharma Dive,
    PR Newswire, and SEC EDGAR. Scores and stores results for the pipeline."""
    from services.linkedin_aggregator import aggregate_all, save_to_db, save_to_json
    try:
        leads = aggregate_all(max_total=50)
        inserted, contacts = save_to_db(leads)
        save_to_json(leads)

        tiers = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        for l in leads:
            tiers[l["tier"]] = tiers.get(l["tier"], 0) + 1

        return {
            "ok": True,
            "total_signals": len(leads),
            "posts_inserted": inserted,
            "contacts_created": contacts,
            "tiers": tiers,
            "sources": list(set(l["source"] for l in leads)),
            "note": "Zero LinkedIn dependency — public data only",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/linkedin/aggregated")
def get_aggregated_intelligence(limit: int = 30):
    """Get the latest aggregated BD intelligence (from public sources). No auth needed."""
    path = BASE_DIR / "frontend" / "data" / "aggregated_intelligence.json"
    if path.exists():
        import json as _json
        with open(path, "r", encoding="utf-8") as f:
            data = _json.load(f)
        leads = data.get("leads", [])[:limit]
        return {
            "total": len(leads),
            "generated": data.get("metadata", {}).get("generated"),
            "source": data.get("metadata", {}).get("source"),
            "leads": leads,
        }
    return {"total": 0, "leads": [], "note": "Run POST /api/linkedin/aggregate first"}


# ── AI Lead Scoring Routes (Phase 3.5) ─────────────────────────────────────────
from services.lead_scorer import scorer as lead_scorer


@app.post("/api/leads/score")
def score_lead(lead: dict, user=Depends(get_current_user)):
    """Score a single lead with AI relevance engine."""
    result = lead_scorer.score(lead)
    return {"ok": True, **result}


@app.post("/api/leads/score-batch")
def score_leads_batch(payload: dict, user=Depends(get_current_user)):
    """Score multiple leads and return sorted by relevance."""
    leads = payload.get("leads", [])
    if not leads:
        raise HTTPException(status_code=400, detail="No leads provided")

    scored = lead_scorer.score_batch(leads)
    summary = {
        "total": len(scored),
        "tier_s": sum(1 for l in scored if l.get("tier") == "S"),
        "tier_a": sum(1 for l in scored if l.get("tier") == "A"),
        "tier_b": sum(1 for l in scored if l.get("tier") == "B"),
        "tier_c": sum(1 for l in scored if l.get("tier") == "C"),
        "tier_d": sum(1 for l in scored if l.get("tier") == "D"),
    }
    return {
        "ok": True,
        "summary": summary,
        "leads": [
            {
                "name": l.get("name"),
                "source_id": l.get("source_id"),
                "total_score": l.get("total_score"),
                "tier": l.get("tier"),
                "breakdown": l.get("breakdown"),
                "explanation": l.get("explanation"),
                "bd_priority": l.get("bd_priority"),
            }
            for l in scored
        ],
    }


@app.get("/api/leads/scoring-metrics")
def get_scoring_metrics(user=Depends(get_current_user)):
    """Get scoring configuration and dimension weights."""
    return {
        "dimension_weights": lead_scorer.weights,
        "biotech_hubs": dict(sorted(BIOTECH_HUB_WEIGHTS.items(), key=lambda x: -x[1])[:10]),
        "stage_values": STAGE_VALUES,
    }


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.3.0", "uptime": datetime.now().isoformat()}


# ── Patent Search Routes (Dashboard widget) ──────────────────────────────────
from services.patent_search import search_patents as patent_search
from services.abbreviation_engine import expand_search as expand_abbreviation, get_abbreviation_meaning


@app.get("/api/abbreviations/expand")
async def api_expand_abbreviation(q: str = ""):
    """Expand biopharma abbreviations with context for scoped search."""
    return expand_abbreviation(q)


@app.get("/api/abbreviations/lookup/{abbr}")
async def api_lookup_abbreviation(abbr: str):
    """Look up a specific biopharma abbreviation."""
    from services.abbreviation_engine import list_abbreviations
    return get_abbreviation_meaning(abbr)


@app.get("/api/abbreviations/list")
async def api_list_abbreviations(category: str = ""):
    """List biopharma abbreviations, optionally by category."""
    from services.abbreviation_engine import list_abbreviations
    return {"abbreviations": list_abbreviations(category or None)}


@app.get("/api/patents/search")
async def search_patents_api(q: str = "", source: str = "google", limit: int = 8):
    """Search patents. Auto-expands biopharma abbreviations for scoped results."""
    if not q:
        return {"total": 0, "results": [], "query": q, "source": source}

    # Auto-expand biopharma abbreviations
    expanded = expand_abbreviation(q)
    search_q = expanded["expanded_query"]
    abbreviations = expanded["expansions"]

    result = patent_search(search_q, limit=limit)
    result["original_query"] = q
    result["expanded_query"] = search_q if search_q != q else None
    result["abbreviations_expanded"] = [a["meaning"] for a in abbreviations]
    return result


# ── Static Files (Frontend) ───────────────────────────────────────────────────
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    print(f"[OK] Medicilon CRO Intelligence Platform v0.3.0")
    print(f"[OK] Database: {DB_PATH}")
    print(f"[OK] Frontend: {FRONTEND_DIR}")
    print(f"[OK] Ready — open http://localhost:8000")

    # Sync existing aggregated_intelligence.json into DB immediately (fast — no network)
    # This ensures the dashboard LinkedIn section has data right away, even after a DB reset.
    try:
        agg_path = BASE_DIR / "frontend" / "data" / "aggregated_intelligence.json"
        if agg_path.exists():
            import json as _json
            from services.linkedin_aggregator import save_to_db
            with open(agg_path, "r", encoding="utf-8") as f:
                agg_data = _json.load(f)
            existing_leads = agg_data.get("leads", [])
            if existing_leads:
                inserted, contacts = save_to_db(existing_leads)
                print(f"[Aggregator] Synced {len(existing_leads)} cached signals into DB ({inserted} new posts)")
    except Exception as e:
        print(f"[Aggregator] Cache sync skipped: {e}")

    # Background: refresh BD intelligence from live sources (non-blocking)
    import threading
    def _initial_aggregation():
        try:
            from services.linkedin_aggregator import aggregate_all, save_to_db, save_to_json
            print("[Aggregator] Running background BD intelligence refresh...")
            leads = aggregate_all(max_total=40)
            inserted, contacts = save_to_db(leads)
            save_to_json(leads)
            print(f"[Aggregator] Refresh complete: {len(leads)} signals, {inserted} new posts")
        except Exception as e:
            print(f"[Aggregator] Background refresh skipped (network offline or deps missing): {e}")
    threading.Thread(target=_initial_aggregation, daemon=True).start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
