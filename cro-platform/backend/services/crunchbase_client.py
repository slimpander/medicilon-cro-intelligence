"""
Crunchbase API v4 Client
Handles company search, funding round lookup, and org detail retrieval.

Authentication: User provides their own Crunchbase API key (stored per-user in DB).
Free tier: https://data.crunchbase.com/docs/using-the-api

Usage:
    client = CrunchbaseClient(api_key="...")
    companies = client.search_companies(keyword="biotech", locations="California")
    funding = client.get_funding_rounds(permalink="relay-therapeutics")
    details = client.get_organization("relay-therapeutics")
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.crunchbase.com/api/v4"

# Categories relevant to Medicilon's BD interests
BIOTECH_CATEGORIES = [
    "biotechnology", "therapeutics", "biopharma", "pharmaceutical",
    "drug-discovery", "oncology", "immunology", "genetics",
    "precision-medicine", "gene-therapy", "cell-therapy",
    "medical-device", "diagnostics", "rna", "protein",
]

# Entity fields we care about
ORG_FIELDS = [
    "identifier", "name", "short_description", "description",
    "location_identifiers", "categories", "website_url",
    "linkedin_url", "num_employees_enum", "founded_on",
    "company_type", "stock_exchange_symbol", "rank_org",
    "funding_stage", "total_funding_usd", "last_funding_at",
]

FUNDING_FIELDS = [
    "identifier", "funding_type", "series", "announced_on",
    "money_raised", "money_raised_usd", "pre_money_valuation",
    "num_investors", "lead_investor_identifiers",
    "investor_identifiers", "is_equity",
]


@dataclass
class CrunchbaseCompany:
    """Normalized company record from Crunchbase"""
    crunchbase_id: str
    name: str
    permalink: str
    description: str = ""
    website: str = ""
    linkedin_url: str = ""
    founded_on: str = ""
    funding_stage: str = ""
    total_funding_usd: int = 0
    num_employees: str = ""
    company_type: str = ""
    categories: list = field(default_factory=list)
    locations: list = field(default_factory=list)
    state: str = ""  # extracted US state
    city: str = ""


@dataclass
class FundingRound:
    """Normalized funding round"""
    crunchbase_id: str
    funding_type: str  # seed, series_a, series_b, etc.
    announced_on: str
    money_raised_usd: int
    money_raised: str  # display string e.g. "$45M"
    num_investors: int = 0
    lead_investors: list = field(default_factory=list)
    valuation_usd: int = 0
    is_equity: bool = True


class CrunchbaseClient:
    """Crunchbase API v4 client with rate limiting and error handling."""

    def __init__(self, api_key: str, timeout: int = 20):
        self.api_key = api_key
        self.timeout = timeout
        self._last_request = 0.0
        self._min_interval = 0.12  # ~8 req/sec (free tier limit)

    def _rate_limit(self):
        """Enforce minimum interval between requests."""
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()

    def _headers(self) -> dict:
        return {
            "X-Cb-User-Key": self.api_key,
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> Optional[dict]:
        """GET request with retry logic."""
        self._rate_limit()
        url = f"{BASE_URL}/{path.lstrip('/')}"
        for attempt in range(3):
            try:
                r = httpx.get(url, headers=self._headers(), params=params,
                              timeout=self.timeout)
                if r.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                    continue
                if r.status_code == 401:
                    logger.error("Crunchbase: Invalid API key")
                    return None
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.warning(f"Crunchbase GET {path}: {e} (attempt {attempt+1})")
                if attempt < 2:
                    time.sleep(3)
        return None

    def _post(self, path: str, body: dict) -> Optional[dict]:
        """POST request (for search queries)."""
        self._rate_limit()
        url = f"{BASE_URL}/{path.lstrip('/')}"
        for attempt in range(3):
            try:
                r = httpx.post(url, headers=self._headers(), json=body,
                               timeout=self.timeout)
                if r.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                    continue
                if r.status_code == 401:
                    logger.error("Crunchbase: Invalid API key")
                    return None
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.warning(f"Crunchbase POST {path}: {e} (attempt {attempt+1})")
                if attempt < 2:
                    time.sleep(3)
        return None

    # ── Company Search ────────────────────────────────────────────────────────

    def search_companies(
        self,
        keyword: str = "",
        categories: list = None,
        locations: list = None,
        funding_stage: str = "",
        founded_after: str = "",
        limit: int = 50,
    ) -> list[CrunchbaseCompany]:
        """
        Search for biotech/pharma companies on Crunchbase.

        Args:
            keyword: Free-text search (company name, description)
            categories: e.g. ["biotechnology", "therapeutics"]
            locations: e.g. ["California", "Massachusetts"]
            funding_stage: e.g. "seed", "early_stage_venture", "late_stage_venture"
            founded_after: ISO date string for filtering by founding date
            limit: Max results (capped at 100 for free tier)
        """
        # Build query
        conditions = []
        conditions.append({"type": "predicate", "field_id": "facet_ids",
                           "operator_id": "includes", "values": ["company"]})

        if keyword:
            conditions.append({"type": "predicate", "field_id": "identifier",
                               "operator_id": "contains", "values": [keyword]})

        if categories:
            cat_ids = [f"category::{c}" for c in categories]
            conditions.append({"type": "predicate", "field_id": "category_ids",
                               "operator_id": "includes_any", "values": cat_ids})

        if locations:
            loc_values = []
            for loc in locations:
                loc_values.append({"type": "value", "value": loc,
                                   "field_id": "location_identifiers",
                                   "properties": "identifier"})
            conditions.append({"type": "predicate", "field_id": "location_identifiers",
                               "operator_id": "includes_any", "values": loc_values})

        if funding_stage:
            conditions.append({"type": "predicate", "field_id": "funding_stage",
                               "operator_id": "eq", "values": [funding_stage]})

        if founded_after:
            conditions.append({"type": "predicate", "field_id": "founded_on",
                               "operator_id": "gte", "values": [founded_after]})

        query = {
            "field_ids": ORG_FIELDS,
            "order": [{"field_id": "rank_org", "sort": "asc"}],
            "query": conditions,
            "limit": min(limit, 100),
        }

        data = self._post("searches/organizations", query)
        if not data:
            return []

        entities = data.get("entities", [])
        results = []
        for ent in entities:
            props = ent.get("properties", {})
            locs = props.get("location_identifiers", [])

            # Extract US state
            state = ""
            city = ""
            for loc in locs:
                if isinstance(loc, dict):
                    if loc.get("location_type") == "state" and loc.get("country_code") == "US":
                        state = loc.get("value", "")[:2].upper()
                    elif loc.get("location_type") == "city":
                        city = loc.get("value", "")

            results.append(CrunchbaseCompany(
                crunchbase_id=ent.get("identifier", {}).get("uuid", ""),
                name=props.get("name", props.get("identifier", {}).get("value", "")),
                permalink=props.get("identifier", {}).get("permalink", ""),
                description=props.get("short_description", "") or "",
                website=props.get("website_url", "") or "",
                linkedin_url=props.get("linkedin_url", "") or "",
                founded_on=props.get("founded_on", "") or "",
                funding_stage=props.get("funding_stage", "") or "",
                total_funding_usd=props.get("total_funding_usd", 0) or 0,
                num_employees=props.get("num_employees_enum", "") or "",
                company_type=props.get("company_type", "") or "",
                categories=[c.get("value","") for c in props.get("categories", [])],
                locations=[{"city": city, "state": state}],
                state=state,
                city=city,
            ))

        return results

    # ── Organization Detail ───────────────────────────────────────────────────

    def get_organization(self, permalink: str) -> Optional[CrunchbaseCompany]:
        """Get detailed information about a specific company."""
        data = self._get(f"entities/organizations/{permalink}",
                         params={"field_ids": ",".join(ORG_FIELDS)})
        if not data:
            return None

        props = data.get("properties", {})
        locs = props.get("location_identifiers", [])

        state = ""
        city = ""
        for loc in locs:
            if isinstance(loc, dict):
                if loc.get("location_type") == "state" and loc.get("country_code") == "US":
                    state = loc.get("value", "")[:2].upper()
                elif loc.get("location_type") == "city":
                    city = loc.get("value", "")

        return CrunchbaseCompany(
            crunchbase_id=data.get("identifier", {}).get("uuid", ""),
            name=props.get("name", props.get("identifier", {}).get("value", "")),
            permalink=props.get("identifier", {}).get("permalink", permalink),
            description=props.get("short_description", "") or props.get("description", "") or "",
            website=props.get("website_url", "") or "",
            linkedin_url=props.get("linkedin_url", "") or "",
            founded_on=props.get("founded_on", "") or "",
            funding_stage=props.get("funding_stage", "") or "",
            total_funding_usd=props.get("total_funding_usd", 0) or 0,
            num_employees=props.get("num_employees_enum", "") or "",
            company_type=props.get("company_type", "") or "",
            categories=[c.get("value","") for c in props.get("categories", [])],
            locations=[{"city": city, "state": state}],
            state=state,
            city=city,
        )

    # ── Funding Rounds ────────────────────────────────────────────────────────

    def get_funding_rounds(
        self,
        permalink: str,
        since: str = "",
        limit: int = 20,
    ) -> list[FundingRound]:
        """Get funding rounds for a specific company."""
        params = {"field_ids": ",".join(FUNDING_FIELDS), "limit": limit}
        if since:
            params["query"] = json.dumps([
                {"type": "predicate", "field_id": "announced_on",
                 "operator_id": "gte", "values": [since]}
            ])

        data = self._get(f"entities/organizations/{permalink}/cards/funding_rounds",
                         params=params)
        if not data:
            return []

        cards = data.get("cards", [])
        results = []
        for card in cards:
            props = card.get("properties", {})
            lead_investors = []
            for inv in props.get("lead_investor_identifiers", []):
                if isinstance(inv, dict):
                    lead_investors.append(inv.get("value", ""))
                else:
                    lead_investors.append(str(inv))

            results.append(FundingRound(
                crunchbase_id=card.get("identifier", {}).get("uuid", ""),
                funding_type=props.get("funding_type", ""),
                announced_on=props.get("announced_on", "") or "",
                money_raised_usd=props.get("money_raised_usd", 0) or 0,
                money_raised=props.get("money_raised", "") or _fmt_usd(props.get("money_raised_usd", 0)),
                num_investors=props.get("num_investors", 0) or 0,
                lead_investors=lead_investors,
                valuation_usd=props.get("pre_money_valuation", {}).get("value_usd", 0) or 0,
                is_equity=props.get("is_equity", True),
            ))

        return results

    # ── Recent Funded Companies (Discovery) ───────────────────────────────────

    def discover_recently_funded(
        self,
        days_back: int = 90,
        min_amount_usd: int = 1_000_000,  # $1M minimum
        states: list = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Discover recently funded biotech companies — the core BD intelligence query.
        Returns normalized lead records matching the intelligence.json format.
        """
        since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        companies = self.search_companies(
            categories=BIOTECH_CATEGORIES[:8],  # Top categories to keep query reasonable
            founded_after="2000-01-01",
            limit=limit,
        )

        leads = []
        for co in companies:
            # Skip if no US state or too small
            if not co.state:
                continue
            if states and co.state not in states:
                continue
            if co.total_funding_usd and co.total_funding_usd < min_amount_usd:
                continue

            # Get recent funding rounds
            rounds = self.get_funding_rounds(co.permalink, since=since)
            if not rounds:
                continue

            # Determine most recent/significant round
            latest = rounds[0]  # sorted by date desc
            total_recent = sum(r.money_raised_usd for r in rounds)

            # Infer CRO service needs from categories
            needs = _infer_needs_from_categories(co.categories)

            signal_parts = []
            if latest.funding_type:
                signal_parts.append(latest.funding_type.replace("_", " ").title())
            if latest.money_raised:
                signal_parts.append(latest.money_raised)
            if latest.announced_on:
                signal_parts.append(f"announced {latest.announced_on}")

            lead = {
                "source": "Crunchbase",
                "source_id": co.crunchbase_id,
                "name": co.name,
                "state": co.state,
                "city": co.city,
                "stage": _map_funding_stage(co.funding_stage),
                "focus": co.description[:120] if co.description else "",
                "needs": needs,
                "signal": " · ".join(signal_parts) if signal_parts else f"Total funding: {_fmt_usd(co.total_funding_usd)}",
                "date": latest.announced_on or co.founded_on or "",
                "date_label": "",
                "url": f"https://www.crunchbase.com/organization/{co.permalink}",
                "score": 0,
                "hub_weight": 0,
                # Enriched fields
                "total_funding_usd": co.total_funding_usd,
                "total_funding_display": _fmt_usd(co.total_funding_usd),
                "recent_round_amount_usd": latest.money_raised_usd,
                "recent_round_amount_display": latest.money_raised or _fmt_usd(latest.money_raised_usd),
                "funding_stage_cb": co.funding_stage,
                "num_employees": co.num_employees,
                "founded_on": co.founded_on,
                "website": co.website,
                "linkedin_url": co.linkedin_url,
                "lead_investors": latest.lead_investors[:3],
                "num_rounds": len(rounds),
            }
            leads.append(lead)

        return sorted(leads, key=lambda l: l.get("recent_round_amount_usd", 0), reverse=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_usd(amount: int) -> str:
    """Format USD amount to human readable string."""
    if not amount:
        return ""
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.0f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount}"


def _map_funding_stage(cb_stage: str) -> str:
    """Map Crunchbase funding stage to our simplified stage labels."""
    mapping = {
        "seed": "Seed/Funding",
        "pre_seed": "Seed/Funding",
        "angel": "Seed/Funding",
        "early_stage_venture": "Funding",
        "series_a": "Funding",
        "series_b": "Funding",
        "late_stage_venture": "Funding",
        "series_c": "Funding",
        "series_d": "Funding",
        "series_e_plus": "Funding",
        "growth_equity": "Funding",
        "private_equity": "Funding",
        "post_ipo_equity": "Public",
        "post_ipo_debt": "Public",
        "ipo": "Public",
    }
    return mapping.get(cb_stage, "Funding")


def _infer_needs_from_categories(categories: list) -> list:
    """Infer CRO service needs from Crunchbase categories."""
    text = " ".join(categories).lower()
    needs = set()

    category_map = {
        "DMPK": ["drug", "therapeutic", "small molecule", "pharmacokinetics"],
        "ADME": ["drug", "therapeutic", "small molecule", "adme"],
        "Toxicology": ["drug", "therapeutic", "toxicology", "safety"],
        "Bioanalysis": ["drug", "biotech", "biomarker", "assay"],
        "CMC": ["drug", "manufacturing", "bioprocess", "formulation"],
        "In Vivo / Mouse Services": ["preclinical", "in vivo", "animal model"],
        "Protein Sciences / Biologics": ["protein", "antibody", "biologic", "biopharma"],
        "Clinical Trials": ["clinical", "trial", "phase"],
        "Biomarker / Genomics": ["genomics", "gene", "sequencing", "biomarker"],
    }

    for service, keywords in category_map.items():
        if any(kw in text for kw in keywords):
            needs.add(service)

    # Default: any biotech company likely needs DMPK + Bioanalysis
    if not needs:
        needs = {"DMPK", "Bioanalysis"}

    return sorted(needs)
