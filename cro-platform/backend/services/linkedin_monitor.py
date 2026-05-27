"""
LinkedIn Monitoring Agent — Post filtering, contact discovery, relevance scoring
Phase 3.4 of the Medicilon CRO Intelligence Platform
"""

import re
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "platform.db"


class LinkedInMonitor:
    """
    LinkedIn monitoring agent that:
    1. Receives scraped posts from the Chrome extension
    2. Scores relevance based on keywords + decision-maker signals
    3. Identifies high-value contacts
    4. Generates BD lead suggestions
    """

    # Biotech/CRO relevant keywords with category weights
    KEYWORD_CATEGORIES = {
        "preclinical_cro": {
            "keywords": [
                "DMPK", "ADME", "drug metabolism", "pharmacokinetics",
                "preclinical", "CRO", "contract research", "toxicology",
                "safety assessment", "IND-enabling", "IND filing",
                "bioanalysis", "bioanalytical", "GLP", "non-GLP",
                "in vivo", "efficacy", "mouse model", "animal study",
            ],
            "weight": 3.0,
        },
        "drug_development": {
            "keywords": [
                "drug discovery", "lead optimization", "hit-to-lead",
                "candidate selection", "SAR", "medicinal chemistry",
                "CMC", "formulation", "biologics", "monoclonal antibody",
                "ADC", "cell therapy", "gene therapy", "RNA",
                "small molecule", "peptide", "PROTAC",
            ],
            "weight": 2.5,
        },
        "outsourcing_signal": {
            "keywords": [
                "outsource", "outsourcing", "CRO partner", "CDMO",
                "vendor", "collaboration", "partnership", "strategic partner",
                "RFP", "request for proposal", "bid",
                "looking for", "seeking", "need a CRO",
            ],
            "weight": 4.0,
        },
        "funding_signal": {
            "keywords": [
                "Series A", "Series B", "Series C", "funding", "raised",
                "financing", "investment", "IPO", "public offering",
                "venture", "seed round", "closed",
            ],
            "weight": 3.5,
        },
        "decision_maker_title": {
            "keywords": [
                "CSO", "Chief Scientific Officer", "VP R&D", "VP Research",
                "Head of Preclinical", "Head of DMPK", "Head of Pharmacology",
                "Director of Toxicology", "SVP Discovery", "CEO", "CTO",
                "Head of Outsourcing", "Director CMC",
            ],
            "weight": 4.0,
        },
    }

    TITLE_KEYWORDS = set(KEYWORD_CATEGORIES["decision_maker_title"]["keywords"])

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.posts_processed = 0
        self.contacts_discovered = 0

    def score_post(self, post: dict) -> dict:
        """
        Score a LinkedIn post for relevance to Medicilon BD.
        Returns enriched post with relevance_score, matched_keywords, contact extraction.
        """
        content = (post.get("content", "") or post.get("text", "") or "").lower()
        author_title = (post.get("author_title", "") or post.get("authorTitle", "") or "").lower()
        author_company = post.get("author_company", "") or post.get("authorCompany", "") or ""
        author_name = post.get("author", "") or post.get("author_name", "") or ""

        total_score = 0.0
        max_possible = 0.0
        matched_keywords = []
        category_matches = {}

        for category, config in self.KEYWORD_CATEGORIES.items():
            cat_matches = []
            for kw in config["keywords"]:
                if category == "decision_maker_title":
                    # Check in author title
                    if kw.lower() in author_title:
                        cat_matches.append(kw)
                else:
                    # Check in post content
                    if kw.lower() in content:
                        cat_matches.append(kw)

            if cat_matches:
                cat_score = len(cat_matches) * config["weight"]
                total_score += cat_score
                max_possible += config["weight"] * 5  # cap per category
                matched_keywords.extend(cat_matches)
                category_matches[category] = cat_matches

        # Bonus signals
        bonuses = 0

        # 1. Contains a URL or link (sharing article/resource = engaged)
        if "http" in content or "linkedin.com" in content:
            bonuses += 5

        # 2. Engagement signals (likes, comments — if available)
        engagement_text = (post.get("engagement", "") or "").lower()
        if "comment" in engagement_text or "like" in engagement_text:
            bonuses += 3

        # 3. Post length (more detailed = more signal)
        if len(content) > 200:
            bonuses += 5
        elif len(content) > 100:
            bonuses += 3

        # 4. Company mentions in biotech hubs
        if any(st.lower() in content for st in ["boston", "cambridge", "san francisco", "san diego", "research triangle", "new jersey"]):
            bonuses += 3

        total_score += bonuses
        max_possible = max(max_possible, 1)

        # Normalize to 0-100
        relevance_score = min(100, round(total_score / max_possible * 100, 1)) if max_possible > 0 else 0

        # Extract contact info
        contact = self._extract_contact(post, author_name, author_title, author_company)

        # Generate BD notes
        bd_notes = self._generate_bd_notes(category_matches, author_title, author_company, author_name)

        return {
            "relevance_score": relevance_score,
            "matched_keywords": matched_keywords,
            "categories_matched": category_matches,
            "contact": contact,
            "bd_notes": bd_notes,
            "is_high_priority": relevance_score >= 70,
        }

    def _extract_contact(self, post: dict, name: str, title: str, company: str) -> Optional[dict]:
        """Extract decision-maker contact from post metadata."""
        if not name:
            return None

        is_decision_maker = any(
            t.lower() in title.lower() for t in self.TITLE_KEYWORDS
        )

        if not is_decision_maker:
            return None

        self.contacts_discovered += 1
        return {
            "name": name,
            "title": title,
            "company": company,
            "source": "LinkedIn post",
            "confidence": "high" if "VP" in title or "Chief" in title or "Head of" in title else "medium",
        }

    def _generate_bd_notes(
        self,
        category_matches: dict,
        author_title: str,
        author_company: str,
        author_name: str,
    ) -> str:
        """Generate actionable BD intelligence notes from a matched post."""
        notes = []

        if "outsourcing_signal" in category_matches:
            notes.append("🔥 ACTIVE OUTSOURCING SIGNAL — potential immediate CRO opportunity")

        if "funding_signal" in category_matches:
            notes.append("💰 Funding event detected — company likely has budget for CRO services")

        is_dm = any(t.lower() in author_title.lower() for t in self.TITLE_KEYWORDS)
        if is_dm:
            notes.append(f"👤 Decision-maker identified: {author_name} ({author_title}) — reach out directly")

        if "preclinical_cro" in category_matches:
            matched = category_matches["preclinical_cro"]
            notes.append(f"🔬 Relevant to Medicilon services: {', '.join(matched[:5])}")

        if "drug_development" in category_matches:
            matched = category_matches["drug_development"]
            notes.append(f"💊 Drug development discussion: {', '.join(matched[:3])}")

        if not notes:
            notes.append("📎 General biotech industry signal — monitor for future developments")

        return " | ".join(notes)

    def process_post_batch(self, posts: list) -> dict:
        """Process a batch of LinkedIn posts and return summary."""
        results = []
        high_priority = []
        contacts = []

        for post in posts:
            scored = self.score_post(post)
            enriched = {**post, **scored}
            results.append(enriched)

            if scored["is_high_priority"]:
                high_priority.append(enriched)

            if scored["contact"]:
                contacts.append(scored["contact"])

        self.posts_processed += len(posts)

        return {
            "posts_processed": len(posts),
            "total_processed": self.posts_processed,
            "high_priority_count": len(high_priority),
            "contacts_found": len(contacts),
            "high_priority": high_priority,
            "contacts": contacts,
            "all_results": results,
        }

    def store_post(self, post: dict) -> int:
        """Store a scored LinkedIn post in the database."""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        source_id = hashlib.md5(
            (post.get("post_url", "") + post.get("author", "") + post.get("content", "")[:50])
            .encode()
        ).hexdigest()

        try:
            conn.execute(
                """INSERT OR REPLACE INTO linkedin_posts
                   (source_id, post_url, author_name, author_title, author_company,
                    content, post_date, relevance_score, matched_keywords, processed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (
                    source_id,
                    post.get("post_url", "") or post.get("url", ""),
                    post.get("author", "") or post.get("author_name", ""),
                    post.get("author_title", "") or post.get("authorTitle", ""),
                    post.get("author_company", "") or post.get("authorCompany", ""),
                    post.get("content", "") or post.get("text", ""),
                    post.get("post_date", "") or post.get("date", ""),
                    post.get("relevance_score", 0),
                    ", ".join(post.get("matched_keywords", [])),
                )
            )
            conn.commit()
        except Exception as e:
            print(f"[LinkedInMonitor] DB store error: {e}")
        finally:
            conn.close()

        return 0

    def store_contact(self, contact: dict) -> int:
        """Store a discovered contact in the database."""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        source_id = hashlib.md5(
            (contact.get("name", "") + contact.get("company", "")).encode()
        ).hexdigest()

        try:
            conn.execute(
                """INSERT OR REPLACE INTO linkedin_contacts
                   (source_id, name, title, company, linkedin_url, relevance_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    source_id,
                    contact.get("name", ""),
                    contact.get("title", ""),
                    contact.get("company", ""),
                    contact.get("linkedin_url", ""),
                    85,
                )
            )
            conn.commit()
        except Exception as e:
            print(f"[LinkedInMonitor] Contact store error: {e}")
        finally:
            conn.close()
        return 0

    def get_weekly_report(self) -> dict:
        """Generate a weekly LinkedIn monitoring report."""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))

        # Posts in last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        posts = conn.execute(
            """SELECT COUNT(*) as cnt, AVG(relevance_score) as avg_score
               FROM linkedin_posts WHERE created_at >= ?""",
            (week_ago,)
        ).fetchone()

        # Top posts
        top_posts = conn.execute(
            """SELECT author_name, author_title, author_company, content, relevance_score, matched_keywords
               FROM linkedin_posts WHERE created_at >= ?
               ORDER BY relevance_score DESC LIMIT 10""",
            (week_ago,)
        ).fetchall()

        # Contacts
        contacts = conn.execute(
            """SELECT COUNT(*) FROM linkedin_contacts WHERE created_at >= ?""",
            (week_ago,)
        ).fetchone()

        conn.close()

        return {
            "period": "Last 7 days",
            "posts_scanned": posts["cnt"] or 0,
            "avg_relevance": round(posts["avg_score"] or 0, 1),
            "contacts_discovered": contacts[0] if contacts else 0,
            "top_matches": [
                {
                    "author": r["author_name"],
                    "title": r["author_title"],
                    "company": r["author_company"],
                    "excerpt": (r["content"] or "")[:150],
                    "score": r["relevance_score"],
                    "keywords": r["matched_keywords"],
                }
                for r in top_posts
            ],
        }


# ── Singleton ──────────────────────────────────────────────────────
monitor = LinkedInMonitor()
