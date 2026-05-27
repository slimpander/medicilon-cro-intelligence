"""
AI Relevance Scoring Engine
Phase 3.5 of the Medicilon CRO Intelligence Platform

Scores potential BD leads across multiple weighted dimensions:
1. Service match with Medicilon capabilities
2. Funding amount and recency
3. Clinical / development stage
4. Geographic proximity to biotech hubs
5. Signal content (descriptions, keywords)
6. Company maturity and CRO spend likelihood
"""

import math
import re
from datetime import datetime, timedelta
from typing import Optional


# ── Scoring Configuration ─────────────────────────────────────────────────────

# Weights for each dimension (total = 100)
DIMENSION_WEIGHTS = {
    "service_match": 30,      # How many of their needs does Medicilon cover?
    "funding_signal": 20,     # Funding amount + recency
    "stage_value": 15,        # Development stage → CRO spend likelihood
    "hub_proximity": 10,      # Geographic location in biotech hubs
    "signal_content": 15,     # Textual signals in descriptions
    "company_maturity": 10,   # Company size, age, public/private
}

# Biotech hub weights (0-10)
BIOTECH_HUB_WEIGHTS = {
    "MA": 10, "CA": 10, "NJ": 9, "NC": 8, "TX": 8, "PA": 7,
    "NY": 7, "MD": 6, "IL": 6, "WA": 6, "CO": 5, "MN": 5,
    "GA": 4, "VA": 4, "FL": 4, "OH": 3, "MI": 3, "IN": 3,
    "WI": 3, "MO": 3, "CT": 6, "OR": 4,
}

# Stage → CRO spend likelihood
STAGE_VALUES = {
    # Late clinical → high spend
    "Phase 3": 100,
    "Phase 2/3": 95,
    # Mid clinical → significant spend
    "Phase 2": 85,
    "Phase 1/2": 80,
    "Phase 1": 75,
    # Preclinical / IND
    "Preclinical": 70,
    "IND-enabling": 75,
    "IND filed": 70,
    # Funded → ready to spend
    "Funding": 65,
    "Seed/Funding": 50,
    "Series A": 55,
    "Series B": 70,
    "Series C": 80,
    "Growth": 85,
    "Public": 90,
    # Early / Academic
    "Discovery": 30,
    "Grant": 25,
    "Academic": 15,
}

# CRO-relevant signal keywords with category weights
SIGNAL_KEYWORDS = {
    "urgent_need": {
        "patterns": [
            r"\b(outsourc|looking for|seeking|need|require)\s+(CRO|preclinical|DMPK|ADME|tox)",
            r"\b(RFP|request for proposal|bid|vendor selection)",
            r"\b(urgent|immediate|priority|ASAP)",
        ],
        "weight": 5,
    },
    "future_need": {
        "patterns": [
            r"\b(planning|preparing|building|expanding)\s+(preclinical|clinical|DMPK)",
            r"\b(IND.filing|IND.enabling|IND.submission)",
            r"\b(coming|upcoming|future|Phase)",
        ],
        "weight": 3,
    },
    "drug_modality": {
        "patterns": [
            r"\b(small molecule|mAb|antibody|ADC|PROTAC|peptide|oligo)",
            r"\b(biologic|cell therapy|gene therapy|mRNA|siRNA|ASO)",
            r"\b(oncology|immuno.oncology|CNS|rare disease|metabolic)",
        ],
        "weight": 2,
    },
    "partnership": {
        "patterns": [
            r"\b(partnership|collaboration|strategic alliance|joint)",
            r"\b(dealmaking|licensing|co.develop)",
        ],
        "weight": 2,
    },
}

# Medicilon core services for matching
MEDICILON_SERVICES = {
    "In Vivo / Mouse Services": ["in vivo", "mouse model", "animal study", "efficacy", "PDX", "xenograft"],
    "DMPK": ["DMPK", "pharmacokinetics", "PK", "drug metabolism", "PK/PD"],
    "ADME": ["ADME", "absorption", "distribution", "excretion", "bioavailability"],
    "Toxicology": ["toxicology", "tox", "safety", "GLP", "non-GLP", "MTD"],
    "Bioanalysis": ["bioanalysis", "bioanalytical", "LC-MS", "ligand binding", "biomarker"],
    "CMC": ["CMC", "formulation", "manufacturing", "process development", "quality control"],
    "Protein Sciences / Biologics": ["protein", "biologics", "antibody", "recombinant", "expression"],
}


class LeadScorer:
    """Scores funding/intelligence leads for BD relevance."""

    def __init__(self, weights: dict = None):
        self.weights = weights or DIMENSION_WEIGHTS

    def score(self, lead: dict) -> dict:
        """
        Score a lead across all dimensions.
        Returns dict with total score + breakdown.
        """
        scores = {}

        # 1. Service match
        scores["service_match"] = self._score_service_match(lead)

        # 2. Funding signal
        scores["funding_signal"] = self._score_funding(lead)

        # 3. Stage value
        scores["stage_value"] = self._score_stage(lead)

        # 4. Hub proximity
        scores["hub_proximity"] = self._score_geography(lead)

        # 5. Signal content
        scores["signal_content"] = self._score_content(lead)

        # 6. Company maturity
        scores["company_maturity"] = self._score_maturity(lead)

        # Weighted total (0-100)
        total = round(sum(
            scores[dim] * (self.weights.get(dim, 0) / 100)
            for dim in scores
        ), 1)

        # Generate explanation
        explanation = self._generate_explanation(scores, lead)

        return {
            "total_score": total,
            "breakdown": scores,
            "tier": self._classify_tier(total),
            "explanation": explanation,
            "bd_priority": self._bd_priority_recommendation(total, scores, lead),
        }

    def score_batch(self, leads: list) -> list:
        """Score multiple leads and return sorted by score."""
        scored = []
        for lead in leads:
            result = self.score(lead)
            scored.append({**lead, **result})
        scored.sort(key=lambda x: x["total_score"], reverse=True)
        return scored

    # ── Dimension Scorers ──────────────────────────────────────────────────

    def _score_service_match(self, lead: dict) -> float:
        """Score based on service overlap with Medicilon capabilities."""
        needs = lead.get("needs", []) or []
        if not needs:
            # Try to infer from signal/description
            needs = self._infer_needs_from_text(lead)

        if not needs:
            return 0.0

        matched = 0
        for need in needs:
            if need in MEDICILON_SERVICES:
                matched += 1
            else:
                # Fuzzy match
                for svc, keywords in MEDICILON_SERVICES.items():
                    if any(kw.lower() in need.lower() for kw in keywords):
                        matched += 0.5
                        break

        if not needs:
            return 15.0  # Neutral baseline

        coverage = matched / max(len(needs), 1)
        return min(100, coverage * 100)

    def _score_funding(self, lead: dict) -> float:
        """Score based on funding amount and recency."""
        total_funding = lead.get("total_funding_usd", 0) or lead.get("total_funding", 0) or 0
        recent_round = lead.get("recent_round_amount_usd", 0) or 0

        score = 0.0

        # Total funding (logarithmic — diminishing returns)
        if total_funding > 0:
            score += min(60, math.log10(total_funding / 1e5) * 15)
        elif total_funding == 0 and lead.get("total_funding_display"):
            score += 20  # Has funding data but amount unknown

        # Recent round bonus
        if recent_round > 0:
            score += min(40, math.log10(recent_round / 1e5) * 10)

        # Recency bonus
        date_str = lead.get("date", "")
        if date_str:
            try:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                days_ago = (datetime.now() - date.replace(tzinfo=None)).days
                if days_ago < 30:
                    score += 20
                elif days_ago < 90:
                    score += 10
                elif days_ago < 180:
                    score += 5
            except (ValueError, TypeError):
                pass

        return min(100, score)

    def _score_stage(self, lead: dict) -> float:
        """Score based on development stage → CRO spend likelihood."""
        stage = lead.get("stage", "").strip()
        if not stage:
            return 30.0  # Unknown — conservative estimate

        # Direct match
        if stage in STAGE_VALUES:
            return STAGE_VALUES[stage]

        # Partial match
        for key, value in STAGE_VALUES.items():
            if key.lower() in stage.lower() or stage.lower() in key.lower():
                return value

        return 30.0

    def _score_geography(self, lead: dict) -> float:
        """Score based on location in biotech hubs."""
        state = lead.get("state", "").upper().strip()[:2]
        if not state:
            return 30.0

        hub_weight = BIOTECH_HUB_WEIGHTS.get(state, 0)
        if hub_weight >= 10:
            return 100.0
        elif hub_weight >= 8:
            return 85.0
        elif hub_weight >= 6:
            return 70.0
        elif hub_weight >= 4:
            return 50.0
        elif hub_weight > 0:
            return 30.0
        else:
            return 15.0  # Not in a known hub

    def _score_content(self, lead: dict) -> float:
        """Score based on textual signals in description/focus/signal."""
        text = " ".join([
            lead.get("focus", ""),
            lead.get("signal", ""),
            lead.get("description", ""),
            lead.get("name", ""),
        ]).lower()

        if not text.strip():
            return 20.0

        score = 0.0
        max_possible = 0.0

        for category, config in SIGNAL_KEYWORDS.items():
            cat_score = 0
            for pattern in config["patterns"]:
                matches = re.findall(pattern, text)
                if matches:
                    cat_score += len(matches) * config["weight"]
            cat_score = min(cat_score, 15)
            cat_score *= (100 / 15)  # Normalize
            score += cat_score
            max_possible += 100

        if max_possible == 0:
            return 20.0

        return min(100, score)

    def _score_maturity(self, lead: dict) -> float:
        """Score based on company maturity indicators."""
        score = 40.0  # Baseline

        stage = (lead.get("stage", "") or "").lower()

        # Public companies are established customers
        if "public" in stage:
            score += 30
        elif any(s in stage for s in ["series c", "series d", "growth"]):
            score += 25
        elif any(s in stage for s in ["series b", "phase 3"]):
            score += 20
        elif any(s in stage for s in ["series a", "phase 2"]):
            score += 10
        elif any(s in stage for s in ["seed", "phase 1", "preclinical"]):
            score += 5

        # Has funding data = more mature
        if lead.get("total_funding_usd") or lead.get("total_funding_display"):
            score += 15

        # Has lead investors
        if lead.get("lead_investors"):
            score += 10

        return min(100, score)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _infer_needs_from_text(self, lead: dict) -> list:
        """Infer service needs from text fields when explicit needs are missing."""
        text = " ".join([
            lead.get("focus", ""),
            lead.get("signal", ""),
            lead.get("description", ""),
        ]).lower()

        inferred = []
        for svc, keywords in MEDICILON_SERVICES.items():
            if any(kw.lower() in text for kw in keywords):
                inferred.append(svc)
        return inferred

    def _classify_tier(self, score: float) -> str:
        if score >= 85:
            return "S"  # Top priority — immediate action
        elif score >= 70:
            return "A"  # High priority
        elif score >= 55:
            return "B"  # Medium priority
        elif score >= 35:
            return "C"  # Monitor
        else:
            return "D"  # Low priority

    def _generate_explanation(self, scores: dict, lead: dict) -> str:
        """Generate human-readable scoring explanation."""
        parts = []

        svc = scores.get("service_match", 0)
        if svc >= 80:
            parts.append(f"Excellent service match ({svc:.0f}%) — {lead.get('name','Company')}'s needs align strongly with Medicilon capabilities")
        elif svc >= 50:
            parts.append(f"Good service match ({svc:.0f}%) — partial overlap with Medicilon services")
        elif svc > 0:
            parts.append(f"Limited service match ({svc:.0f}%)")

        fund = scores.get("funding_signal", 0)
        if fund >= 70:
            parts.append("Strong funding signal — significant budget for CRO services")
        elif fund >= 40:
            parts.append("Moderate funding — likely has CRO budget")

        stage = scores.get("stage_value", 0)
        stage_name = lead.get("stage", "Unknown")
        if stage >= 80:
            parts.append(f"Late-stage ({stage_name}) — high CRO spend probability")
        elif stage >= 60:
            parts.append(f"Mid-stage ({stage_name}) — active development window")

        geo = scores.get("hub_proximity", 0)
        if geo >= 80:
            parts.append(f"Located in major biotech hub ({lead.get('state','')})")

        return " | ".join(parts) if parts else "Insufficient data for detailed scoring"

    def _bd_priority_recommendation(self, total: float, scores: dict, lead: dict) -> str:
        """Generate actionable BD recommendation."""
        name = lead.get("name", "Company")

        if total >= 85:
            return (
                f"🚀 PRIORITY: {name} is a top-tier lead. "
                f"Strong service match + significant funding = immediate outreach opportunity. "
                f"Prepare capability deck and reach out within 48 hours."
            )
        elif total >= 70:
            return (
                f"📋 HIGH: {name} should be actively pursued. "
                f"Good alignment with Medicilon services. "
                f"Research decision-makers on LinkedIn and send introductory email this week."
            )
        elif total >= 55:
            return (
                f"👀 MONITOR: {name} is worth tracking. "
                f"Add to watchlist and revisit when funding rounds or development milestones occur."
            )
        elif total >= 35:
            return (
                f"📎 WATCHLIST: {name} — limited signal currently. "
                f"Set alert for future funding events."
            )
        else:
            return f"Low priority at this time. Re-evaluate if company profile changes."


# ── Singleton ──────────────────────────────────────────────────────
scorer = LeadScorer()
