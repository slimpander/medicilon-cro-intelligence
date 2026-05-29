"""
SciLeads Client — Reverse-engineered API client for portal.scileads.com
=======================================================================

Authentication: Bearer JWT token (extracted from browser DevTools).
Endpoint:        POST https://portal.scileads.com/api/search/researcher
Backend:         ASP.NET Core (Kestrel) behind CloudFront
Query syntax:    Elasticsearch/Lucene (AND, OR, field:value, Category:(...))

The token is stored in Settings → scilead_token.
It can be refreshed via POST /api/refresh-token.

Usage:
    client = SciLeadClient(token="eyJh...")
    results = await client.search_researchers("BMS", categories=["Funding", "ClinicalTrials"], count=50)
    for r in results.grouped_results:
        print(f"{r.researcher_first_name} {r.researcher_last_name}: {r.researcher_email}")
"""

import time
import uuid
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://portal.scileads.com"
SEARCH_ENDPOINT = "/api/search/researcher"
REFRESH_TOKEN_ENDPOINT = "/api/refresh-token"

# ═══════════════════════════════════════════════════════════════════════════════
# Response Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Publication:
    citation_id: int = 0
    article_title: str = ""
    journal_title: str = ""
    total_collaborators: int = 0
    date: str = ""
    cited: int = 0
    journal_impact_factor: float = 0.0
    category: str = "Publication"

@dataclass
class Poster:
    sci_leads_tradeshow_id: int = 0
    sci_leads_poster_id: int = 0
    show: str = ""
    year: str = ""
    title: str = ""
    session_type: str = ""
    date: str = ""
    session_start_date: str = ""
    category: str = "Tradeshow"
    end_date: str = ""
    country: str = ""
    state: str = ""
    city: str = ""

@dataclass
class ClinicalTrial:
    nct_id: str = ""
    researcher_role: str = ""
    date: str = ""
    study_type: str = ""
    title: str = ""
    overall_status: str = ""
    phase: str = ""
    lead_sponsor: str = ""
    lead_sponsor_super_org: int = 0
    category: str = "Trial"

@dataclass
class Researcher:
    """Full researcher record from SciLeads."""
    researcher_id: int = 0
    researcher_first_name: str = ""
    researcher_last_name: str = ""
    researcher_middle_name: str = ""
    researcher_email: str = ""
    researcher_phone: str = ""
    researcher_linkedin: str = ""
    researcher_scraped_source: int = 0

    # Email metadata
    email_shared: bool = False
    email_publicly_sourced: bool = False
    email_status_category: str = ""       # SafeToSend / Uncertain
    email_last_alive_check_date: str = ""

    # Organisation
    organisation_name: str = ""
    organisation_city: str = ""
    organisation_country: str = ""
    organisation_state: str = ""
    organisation_category_group: List[str] = field(default_factory=list)
    sci_leads_organisation_id: int = 0
    super_organisation_id: int = 0
    organisation_start_date: str = ""

    # Job
    job_title: str = ""
    job_start_date: str = ""
    previous_job_title: str = ""

    # Counts
    total_matches: int = 0
    total_publications: int = 0
    total_funded_projects: int = 0
    total_tradeshow_sessions: int = 0
    total_clinical_trials: int = 0
    total_collaborators: int = 0
    total_collaborators_overall: int = 0

    # Researcher-level totals (lifetime)
    researchers_total_publications: int = 0
    researchers_total_funded_projects: int = 0
    researchers_total_trade_show_sessions: int = 0
    researchers_total_clinical_trials: int = 0

    # Author metrics
    total_last_named_author_count: int = 0
    total_first_named_author_count: int = 0

    # Scoring
    relevance_score: float = 0.0

    # Dates
    most_recent_date: str = ""
    most_recent_date_time: str = ""

    # Impact metrics
    three_year_h_index_average: float = 0.0
    three_year_h_index_total: int = 0
    three_year_sjr_average: float = 0.0
    three_year_sjr_total: float = 0.0
    all_time_h_index_average: float = 0.0
    all_time_h_index_total: int = 0
    all_time_sjr_average: float = 0.0
    all_time_sjr_total: float = 0.0

    # Funding
    three_year_total_funding: float = 0.0
    all_time_total_funding: float = 0.0

    # Categorisation
    document_category: List[str] = field(default_factory=list)
    top_mesh_topics: List[str] = field(default_factory=list)
    journal_categories: List[str] = field(default_factory=list)
    journal_top_categories: List[str] = field(default_factory=list)

    # Nested data
    publications: List[Publication] = field(default_factory=list)
    posters: List[Poster] = field(default_factory=list)
    clinical_trials: List[ClinicalTrial] = field(default_factory=list)
    funding: List[Dict] = field(default_factory=list)


@dataclass
class SearchResponse:
    """Top-level response from /api/search/researcher."""
    new_search_performed: bool = True
    count: int = 0                      # page size
    total_results: int = 0
    distinct_super_researchers_count: int = 0
    email_count: int = 0
    total_emails: int = 0
    organisation_count: int = 0
    total_organisations: int = 0
    country_count: int = 0
    distinct_shows: int = 0
    has_more: bool = False
    total_funding_count: int = 0
    total_posters: int = 0
    total_publications: int = 0
    total_clinical_trials: int = 0
    large_export: bool = False
    milliseconds: int = 0
    term_count: int = 0
    grouped_results: List[Researcher] = field(default_factory=list)
    visualisations: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Client
# ═══════════════════════════════════════════════════════════════════════════════

VALID_CATEGORIES = ["Publications", "ClinicalTrials", "Tradeshows", "Funding", "Profile"]


class SciLeadClient:
    """Authenticated client for the SciLeads internal search API.

    Token is extracted from browser DevTools (Application → Local Storage,
    or Network tab → Request Headers → Authorization: Bearer <token>).

    Rate Limiting: SciLeads uses a credit-based system. To avoid detection:
    - Minimum 0.5s delay between requests
    - Random jitter added to each delay
    - Concurrent requests are serialised
    - Large page fetches are capped at 100 results per call
    """

    MIN_DELAY = 0.5       # minimum seconds between API calls
    MAX_JITTER = 1.0      # random extra delay 0-1s
    MAX_PAGE_SIZE = 100   # cap single-request result count

    def __init__(self, token: str = "", timeout: int = 30):
        self.token = token
        self.timeout = timeout
        self._last_auth_ok = bool(token)
        self._last_request_time = 0.0

    # ── Auth ──────────────────────────────────────────────────────────────

    async def _throttle(self):
        """Enforce minimum delay between API calls to avoid rate-limit detection."""
        import random
        now = time.time()
        elapsed = now - self._last_request_time
        min_wait = self.MIN_DELAY + random.uniform(0, self.MAX_JITTER)
        if elapsed < min_wait:
            delay = min_wait - elapsed
            logger.debug(f"SciLeads throttling: waiting {delay:.2f}s")
            await self._async_sleep(delay)
        self._last_request_time = time.time()

    @staticmethod
    async def _async_sleep(seconds: float):
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)

    @property
    def authenticated(self) -> bool:
        return bool(self.token)

    async def test_auth(self) -> bool:
        """Check if the current token is valid by making a minimal query."""
        if not self.token:
            return False
        try:
            await self._throttle()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{BASE_URL}{SEARCH_ENDPOINT}",
                    json=self._build_query("test", count=1),
                    headers=self._headers(),
                )
                return r.status_code == 200
        except Exception as e:
            logger.warning(f"SciLeads auth test failed: {e}")
            return False

    async def _ensure_fresh_token(self) -> bool:
        """Try to refresh the token before making an API call.
        Returns True if token is usable (original or refreshed).
        """
        if not self.token:
            return False

        # Always try refreshing first — token is short-lived
        refreshed = await self.refresh_token()
        if refreshed:
            return True

        # Refresh failed, but original token might still be valid
        # (refresh endpoint may only work near expiry)
        return True  # Let the actual API call determine validity

    async def refresh_token(self) -> bool:
        """Attempt to refresh the JWT via /api/refresh-token."""
        if not self.token:
            return False
        try:
            await self._throttle()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{BASE_URL}{REFRESH_TOKEN_ENDPOINT}",
                    headers=self._headers(),
                )
                if r.status_code == 200:
                    data = r.json()
                    new_token = data.get("token") or data.get("accessToken") or data.get("access_token")
                    if new_token and new_token != self.token:
                        self.token = new_token
                        self._token_updated = True
                        logger.info("SciLeads token refreshed successfully")
                        return True
                    elif new_token == self.token:
                        logger.info("SciLeads token refresh returned same token — already current")
                        return True
                # 400/401 might mean refresh not supported or token too old
                logger.debug(f"SciLeads token refresh returned HTTP {r.status_code} — will try existing token")
                return False
        except Exception as e:
            logger.debug(f"SciLeads token refresh attempt: {e}")
            return False

    @property
    def token_changed(self) -> bool:
        """Whether the token was updated by refresh — caller should persist it."""
        return getattr(self, '_token_updated', False)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
        }

    # ── Query Construction ────────────────────────────────────────────────

    def _build_query(
        self,
        keyword: str = "",
        categories: Optional[List[str]] = None,
        filters: Optional[Dict] = None,
        count: int = 50,
        from_offset: int = 0,
        order: str = "TotalMatches",
        order_by: str = "desc",
    ) -> dict:
        """Build an Elasticsearch/Lucene query for the SciLeads API.

        Args:
            keyword: Search term (org name, drug name, disease, etc.)
            categories: Filter to specific categories. Defaults to all 5.
            filters: Additional filter dict (empty {} for no filters).
            count: Page size (max observed: 4000).
            from_offset: Pagination offset.
            order: Sort field (TotalMatches, relevanceScore, etc.)
            order_by: Sort direction (asc / desc).
        """
        if categories is None:
            categories = VALID_CATEGORIES

        cat_query = " OR ".join(f'"{c}"' for c in categories)
        if keyword:
            query = f"({keyword}) AND Category:({cat_query})"
            highlight = f"({keyword})"
        else:
            query = f"Category:({cat_query})"
            highlight = ""

        return {
            "id": str(uuid.uuid4()),
            "query": query,
            "highlightQuery": highlight,
            "count": count,
            "from": from_offset,
            "order": order,
            "orderBy": order_by,
            "filters": filters or {},
            "nestedQueries": [],
        }

    # ── Parsing ───────────────────────────────────────────────────────────

    def _parse_researcher(self, raw: dict) -> Researcher:
        """Parse a single groupedResults entry into a Researcher dataclass."""
        return Researcher(
            researcher_id=raw.get("researcherId", 0),
            researcher_first_name=raw.get("researcherFirstName", ""),
            researcher_last_name=raw.get("researcherLastName", ""),
            researcher_middle_name=raw.get("researcherMiddleName", ""),
            researcher_email=raw.get("researcherEmail", ""),
            researcher_phone=raw.get("researcherPhone", ""),
            researcher_linkedin=raw.get("researcherLinkedIn", ""),
            researcher_scraped_source=raw.get("researcherScrapedSource", 0),

            email_shared=raw.get("emailShared", False),
            email_publicly_sourced=raw.get("emailPubliclySourced", False),
            email_status_category=raw.get("emailStatusCategory", ""),
            email_last_alive_check_date=raw.get("emailLastAliveCheckDate", ""),

            organisation_name=raw.get("organisationName", ""),
            organisation_city=raw.get("organisationCity", ""),
            organisation_country=raw.get("organisationCountry", ""),
            organisation_state=raw.get("organisationState", ""),
            organisation_category_group=raw.get("organisationCategoryGroup") or [],
            sci_leads_organisation_id=raw.get("sciLeadsOrganisationId", 0),
            super_organisation_id=raw.get("superOrganisationId", 0),
            organisation_start_date=raw.get("organisationStartDate", ""),

            job_title=raw.get("jobTitle", ""),
            job_start_date=raw.get("jobStartDate", ""),
            previous_job_title=raw.get("previousJobTitle", ""),

            total_matches=raw.get("totalMatches", 0),
            total_publications=raw.get("totalPublications", 0),
            total_funded_projects=raw.get("totalFundedProjects", 0),
            total_tradeshow_sessions=raw.get("totalTradeshowSessions", 0),
            total_clinical_trials=raw.get("totalClinicalTrials", 0),
            total_collaborators=raw.get("totalCollaborators", 0),
            total_collaborators_overall=raw.get("totalCollaboratorsOverall", 0),

            researchers_total_publications=raw.get("researchersTotalPublications", 0),
            researchers_total_funded_projects=raw.get("researchersTotalFundedProjects", 0),
            researchers_total_trade_show_sessions=raw.get("researchersTotalTradeShowSessions", 0),
            researchers_total_clinical_trials=raw.get("researchersTotalClinicalTrials", 0),

            total_last_named_author_count=raw.get("totalLastNamedAuthorCount", 0),
            total_first_named_author_count=raw.get("totalFirstNamedAuthorCount", 0),

            relevance_score=raw.get("relevanceScore", 0.0),

            most_recent_date=raw.get("mostRecentDate", ""),
            most_recent_date_time=raw.get("mostRecentDateTime", ""),

            three_year_h_index_average=raw.get("threeYearHIndexAverage", 0.0),
            three_year_h_index_total=raw.get("threeYearHIndexTotal", 0),
            three_year_sjr_average=raw.get("threeYearSJRAverage", 0.0),
            three_year_sjr_total=raw.get("threeYearSJRTotal", 0.0),
            all_time_h_index_average=raw.get("allTimeHIndexAverage", 0.0),
            all_time_h_index_total=raw.get("allTimeHIndexTotal", 0),
            all_time_sjr_average=raw.get("allTimeSJRAverage", 0.0),
            all_time_sjr_total=raw.get("allTimeSJRTotal", 0.0),

            three_year_total_funding=raw.get("threeYearTotalFunding", 0.0),
            all_time_total_funding=raw.get("allTimeTotalFunding", 0.0),

            document_category=raw.get("documentCategory") or [],
            top_mesh_topics=raw.get("topMeshTopics") or [],
            journal_categories=raw.get("journalCategories") or [],
            journal_top_categories=raw.get("journalTopCategories") or [],

            publications=[
                Publication(
                    citation_id=p.get("citationId", 0),
                    article_title=p.get("articleTitle", ""),
                    journal_title=p.get("journalTitle", ""),
                    total_collaborators=p.get("totalCollaborators", 0),
                    date=p.get("date", ""),
                    cited=p.get("cited", 0),
                    journal_impact_factor=p.get("journalImpactFactor", 0.0),
                    category=p.get("category", "Publication"),
                )
                for p in (raw.get("publications") or [])
            ],

            posters=[
                Poster(
                    sci_leads_tradeshow_id=p.get("sciLeadsTradeShowId", 0),
                    sci_leads_poster_id=p.get("sciLeadsPosterId", 0),
                    show=p.get("show", ""),
                    year=p.get("year", ""),
                    title=p.get("title", ""),
                    session_type=p.get("sessionType", ""),
                    date=p.get("date", ""),
                    session_start_date=p.get("sessionStartDate", ""),
                    category=p.get("category", "Tradeshow"),
                    end_date=p.get("endDate", ""),
                    country=p.get("country", ""),
                    state=p.get("state", ""),
                    city=p.get("city", ""),
                )
                for p in (raw.get("posters") or [])
            ],

            clinical_trials=[
                ClinicalTrial(
                    nct_id=t.get("nctId", ""),
                    researcher_role=t.get("researcherRole", ""),
                    date=t.get("date", ""),
                    study_type=t.get("studyType", ""),
                    title=t.get("title", ""),
                    overall_status=t.get("overallStatus", ""),
                    phase=t.get("phase", ""),
                    lead_sponsor=t.get("leadSponsor", ""),
                    lead_sponsor_super_org=t.get("leadSponsorSuperOrg", 0),
                    category=t.get("category", "Trial"),
                )
                for t in (raw.get("clinicalTrials") or [])
            ],

            funding=raw.get("funding") or [],
        )

    def _parse_response(self, raw: dict) -> SearchResponse:
        """Parse the full API response."""
        return SearchResponse(
            new_search_performed=raw.get("newSearchPerformed", True),
            count=raw.get("count", 0),
            total_results=raw.get("totalResults", 0),
            distinct_super_researchers_count=raw.get("distinctSuperResearchersCount", 0),
            email_count=raw.get("emailCount", 0),
            total_emails=raw.get("totalEmails", 0),
            organisation_count=raw.get("organisationCount", 0),
            total_organisations=raw.get("totalOrganisations", 0),
            country_count=raw.get("countryCount", 0),
            distinct_shows=raw.get("distinctShows", 0),
            has_more=raw.get("hasMore", False),
            total_funding_count=raw.get("totalFunding", 0),
            total_posters=raw.get("totalPosters", 0),
            total_publications=raw.get("totalPublications", 0),
            total_clinical_trials=raw.get("totalClinicalTrials", 0),
            large_export=raw.get("largeExport", False),
            milliseconds=raw.get("milliseconds", 0),
            term_count=raw.get("termCount", 0),
            grouped_results=[
                self._parse_researcher(r)
                for r in (raw.get("groupedResults") or [])
            ],
            visualisations=raw.get("visualisations", {}),
        )

    # ── Search ────────────────────────────────────────────────────────────

    async def search_researchers(
        self,
        keyword: str = "",
        categories: Optional[List[str]] = None,
        filters: Optional[Dict] = None,
        count: int = 50,
        from_offset: int = 0,
        order: str = "TotalMatches",
        order_by: str = "desc",
    ) -> SearchResponse:
        """Search for researchers on SciLeads.

        Args:
            keyword: Search term (company name, drug, disease, etc.)
            categories: Category filter list. Defaults to all 5.
            filters: Additional Elasticsearch filters.
            count: Results per page. Max observed: 4000.
            from_offset: Pagination offset.
            order: Sort field.
            order_by: Sort direction.

        Returns:
            SearchResponse with parsed researcher records.
        """
        if not self.token:
            raise ValueError("No SciLeads token configured. Set in Settings → SciLead Token.")

        # Auto-refresh token before each search
        await self._ensure_fresh_token()

        # Cap page size to avoid triggering rate limits
        count = min(count, self.MAX_PAGE_SIZE)

        query = self._build_query(
            keyword=keyword,
            categories=categories,
            filters=filters,
            count=count,
            from_offset=from_offset,
            order=order,
            order_by=order_by,
        )

        await self._throttle()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{BASE_URL}{SEARCH_ENDPOINT}",
                json=query,
                headers=self._headers(),
            )
            r.raise_for_status()
            return self._parse_response(r.json())

    async def search_all_pages(
        self,
        keyword: str = "",
        categories: Optional[List[str]] = None,
        filters: Optional[Dict] = None,
        max_results: int = 500,
        page_size: int = 200,
    ) -> List[Researcher]:
        """Fetch all pages of results for a search query.

        Keeps fetching while has_more is true, up to max_results.
        """
        all_results: List[Researcher] = []
        offset = 0

        while len(all_results) < max_results:
            resp = await self.search_researchers(
                keyword=keyword,
                categories=categories,
                filters=filters,
                count=min(page_size, max_results - len(all_results)),
                from_offset=offset,
            )

            if not resp.grouped_results:
                break

            all_results.extend(resp.grouped_results)
            offset += len(resp.grouped_results)

            if not resp.has_more:
                break

        return all_results

    # ── Convenience Methods ───────────────────────────────────────────────

    async def search_by_organisation(self, org_name: str, **kwargs) -> SearchResponse:
        """Search for researchers at a specific organisation."""
        return await self.search_researchers(keyword=org_name, **kwargs)

    async def search_by_drug(self, drug_name: str, **kwargs) -> SearchResponse:
        """Search for researchers working on a specific drug/compound."""
        return await self.search_researchers(keyword=drug_name, **kwargs)

    async def search_industry_contacts(
        self,
        org_name: str,
        min_relevance: float = 0.0,
        decision_maker_titles: Optional[List[str]] = None,
        **kwargs,
    ) -> List[Researcher]:
        """Search for industry contacts at a company, filtered to decision-makers.

        Args:
            org_name: Target company name.
            min_relevance: Minimum relevance score threshold.
            decision_maker_titles: Title keywords to filter (VP, Director, Head, etc.)
        """
        if decision_maker_titles is None:
            decision_maker_titles = [
                "VP", "Vice President", "SVP", "Senior Vice President",
                "Director", "Executive Director", "Head", "Chief",
                "President", "CEO", "CSO", "COO", "CTO", "CMO",
                "Global Head", "Senior Director", "Associate VP",
            ]

        resp = await self.search_researchers(
            keyword=org_name,
            categories=["Profile", "Publications", "Tradeshows", "ClinicalTrials", "Funding"],
            **kwargs,
        )

        results = []
        for r in resp.grouped_results:
            # Filter by organisation category
            if "Industry" not in (r.organisation_category_group or []):
                continue

            # Filter by relevance
            if r.relevance_score < min_relevance:
                continue

            # Filter by decision-maker title
            if decision_maker_titles:
                title_lower = (r.job_title or "").lower()
                if not any(dm.lower() in title_lower for dm in decision_maker_titles):
                    continue

            results.append(r)

        # Sort by relevance score descending
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results

    async def search_kols(
        self,
        disease_area: str,
        min_h_index: float = 20.0,
        min_publications: int = 20,
        **kwargs,
    ) -> List[Researcher]:
        """Search for Key Opinion Leaders in a disease area.

        Filters academics with strong publication records.
        """
        resp = await self.search_researchers(
            keyword=disease_area,
            categories=["Publications", "ClinicalTrials"],
            order="TotalMatches",
            **kwargs,
        )

        results = []
        for r in resp.grouped_results:
            if r.researchers_total_publications < min_publications:
                continue
            if r.three_year_h_index_average < min_h_index:
                continue
            results.append(r)

        results.sort(key=lambda x: x.three_year_h_index_average, reverse=True)
        return results

    async def search_recent_publications(
        self,
        keyword: str = "",
        months: int = 6,
        **kwargs,
    ) -> List[Researcher]:
        """Find researchers with recent publications matching a keyword.

        Useful for identifying active labs/PIs in a therapeutic area.
        """
        resp = await self.search_researchers(
            keyword=keyword,
            categories=["Publications"],
            order="TotalMatches",
            **kwargs,
        )

        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=months * 30)).isoformat()

        results = []
        for r in resp.grouped_results:
            recent_pubs = [
                p for p in r.publications
                if p.date >= cutoff
            ]
            if recent_pubs:
                results.append(r)

        results.sort(key=lambda x: len([
            p for p in x.publications
            if p.date >= cutoff
        ]), reverse=True)
        return results

    async def search_clinical_trial_pis(
        self,
        keyword: str = "",
        phase: Optional[str] = None,
        status: Optional[str] = "Recruiting",
        **kwargs,
    ) -> List[Researcher]:
        """Find PIs running clinical trials in a specific area.

        Args:
            keyword: Drug, disease, or company.
            phase: Trial phase filter (Phase 1, Phase 2, Phase 3).
            status: Trial status filter (Recruiting, Active, etc.)
        """
        resp = await self.search_researchers(
            keyword=keyword,
            categories=["ClinicalTrials"],
            order="TotalMatches",
            **kwargs,
        )

        results = []
        for r in resp.grouped_results:
            if not r.clinical_trials:
                continue

            filtered_trials = r.clinical_trials
            if phase:
                filtered_trials = [t for t in filtered_trials if phase.lower() in (t.phase or "").lower()]
            if status:
                filtered_trials = [t for t in filtered_trials if status.lower() in (t.overall_status or "").lower()]

            if filtered_trials:
                results.append(r)

        results.sort(key=lambda x: len(x.clinical_trials), reverse=True)
        return results

    # ── BD Lead Generation ────────────────────────────────────────────────

    async def generate_bd_leads(
        self,
        services: Optional[List[str]] = None,
        min_email_quality: str = "SafeToSend",
        **kwargs,
    ) -> List[dict]:
        """Generate BD leads from SciLeads data.

        Searches for industry contacts with active clinical programs or
        recent publications, filtered to decision-makers with good emails.

        Args:
            services: CRO services to match against (DMPK, Bioanalysis, etc.)
            min_email_quality: Minimum email status (SafeToSend, Uncertain)
        """
        if services is None:
            services = ["DMPK", "Bioanalysis", "Toxicology", "CMC"]

        results = []

        # Search across all categories for decision-makers
        for service in services:
            try:
                contacts = await self.search_industry_contacts(
                    org_name=service,
                    min_relevance=0.1,
                    count=20,
                )
                results.extend(contacts)
            except Exception as e:
                logger.warning(f"SciLeads BD search for '{service}' failed: {e}")

        # Deduplicate by researcher_id
        seen = set()
        unique = []
        for r in results:
            if r.researcher_id not in seen:
                seen.add(r.researcher_id)
                unique.append(r)

        # Filter by email quality
        if min_email_quality:
            quality_order = {
                "SafeToSend": 0,
                "Uncertain": 1,
                "": 2,
            }
            unique = [
                r for r in unique
                if quality_order.get(r.email_status_category, 2) <= quality_order.get(min_email_quality, 1)
            ]

        # Format as BD leads
        leads = []
        for r in unique:
            # Determine signal type
            signals = []
            if r.clinical_trials:
                signals.append(f"{len(r.clinical_trials)} clinical trials")
            if r.publications:
                signals.append(f"{len(r.publications)} recent publications")
            if r.posters:
                signals.append(f"Presenting at {r.posters[0].show}" if r.posters else "")
            signals = [s for s in signals if s]

            leads.append({
                "source": "SciLeads",
                "source_id": str(r.researcher_id),
                "name": f"{r.researcher_first_name} {r.researcher_last_name}",
                "email": r.researcher_email,
                "email_quality": r.email_status_category,
                "title": r.job_title,
                "company": r.organisation_name,
                "company_type": ", ".join(r.organisation_category_group or []),
                "state": r.organisation_state,
                "country": r.organisation_country,
                "linkedin": r.researcher_linkedin,
                "relevance_score": r.relevance_score,
                "h_index_3yr": r.three_year_h_index_average,
                "total_publications": r.researchers_total_publications,
                "total_clinical_trials": r.researchers_total_clinical_trials,
                "signals": signals,
                "top_mesh": (r.top_mesh_topics or [])[:5],
                "most_recent_date": r.most_recent_date,
            })

        # Sort: SafeToSend emails first, then by relevance
        leads.sort(key=lambda l: (
            0 if l["email_quality"] == "SafeToSend" else 1,
            -(l["relevance_score"] or 0),
        ))

        return leads
