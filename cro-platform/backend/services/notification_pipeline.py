"""
Notification Pipeline — Email digests, desktop push, scheduled alerts
Phase 3.6 of the Medicilon CRO Intelligence Platform

Features:
- Email digest (morning/afternoon/evening)
- Desktop push notifications via browser
- Scheduled notification generation
- Lead activity alerts based on AI scores
"""

import smtplib
import json
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "platform.db"


class NotificationPipeline:
    """
    Handles generation and delivery of BD intelligence notifications.
    Supports email digest and desktop push delivery channels.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH

    # ── Email Digest ────────────────────────────────────────────────────────

    def send_email_digest(
        self,
        to_email: str,
        smtp_config: dict = None,
        user_id: int = None,
        period: str = "daily",
    ) -> dict:
        """
        Generate and send an email digest of high-priority leads and LinkedIn activity.

        Args:
            to_email: Recipient email address
            smtp_config: Dict with host, port, username, password (or use env vars)
            user_id: User ID for personalized digest
            period: 'morning', 'afternoon', 'evening', or 'daily'

        Returns:
            dict with status and details
        """
        # Default SMTP config
        smtp = smtp_config or {
            "host": "smtp.medicilon.com",
            "port": 587,
            "username": None,
            "password": None,
            "use_tls": True,
        }

        # Gather content
        content = self._gather_digest_content(user_id, period)

        if not content["has_content"]:
            return {"sent": False, "reason": "No new activity to report"}

        # Build email
        html = self._build_digest_html(content, period)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = self._digest_subject(content, period)
        msg["From"] = smtp.get("from_address", "medicilon-intelligence@medicilon.com")
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))

        try:
            server = smtplib.SMTP(smtp["host"], smtp["port"], timeout=10)
            if smtp.get("use_tls", True):
                server.starttls()
            if smtp.get("username") and smtp.get("password"):
                server.login(smtp["username"], smtp["password"])
            server.send_message(msg)
            server.quit()

            self._log_notification(
                user_id,
                f"Email digest sent: {content['new_high_leads']} high-priority leads, "
                f"{content['new_posts']} LinkedIn matches",
            )

            return {"sent": True, "recipient": to_email, "content_summary": content["summary"]}
        except (smtplib.SMTPException, OSError) as e:
            return {"sent": False, "error": f"SMTP error: {str(e)}. Configure SMTP in Settings."}

    def _gather_digest_content(self, user_id: int = None, period: str = "daily") -> dict:
        """Gather content for the digest from the database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        # Time window
        now = datetime.now()
        if period == "morning":
            since = (now.replace(hour=0, minute=0, second=0) - timedelta(hours=15))
        elif period == "afternoon":
            since = now.replace(hour=0, minute=0, second=0)
        elif period == "evening":
            since = now.replace(hour=12, minute=0, second=0)
        else:
            since = now - timedelta(hours=24)

        since_str = since.isoformat()

        # High-priority LinkedIn posts
        posts = conn.execute(
            """SELECT * FROM linkedin_posts
               WHERE relevance_score >= 50 AND created_at >= ?
               ORDER BY relevance_score DESC LIMIT 10""",
            (since_str,)
        ).fetchall()

        # New notifications (high-priority)
        notifications = conn.execute(
            """SELECT * FROM notifications
               WHERE created_at >= ?
               ORDER BY created_at DESC LIMIT 10""",
            (since_str,)
        ).fetchall()

        # LinkedIn stats summary
        total_posts = conn.execute(
            "SELECT COUNT(*) FROM linkedin_posts WHERE created_at >= ?", (since_str,)
        ).fetchone()[0]
        high_priority = conn.execute(
            "SELECT COUNT(*) FROM linkedin_posts WHERE relevance_score >= 70 AND created_at >= ?",
            (since_str,)
        ).fetchone()[0]
        contacts = conn.execute(
            "SELECT COUNT(*) FROM linkedin_contacts WHERE created_at >= ?", (since_str,)
        ).fetchone()[0]

        conn.close()

        has_content = bool(posts) or bool(notifications)

        return {
            "has_content": has_content,
            "period": period,
            "timestamp": now.isoformat(),
            "new_posts": total_posts,
            "new_high_leads": high_priority,
            "new_contacts": contacts,
            "top_posts": [dict(p) for p in posts],
            "notifications": [dict(n) for n in notifications],
            "summary": (
                f"{total_posts} new LinkedIn posts, {high_priority} high-priority, "
                f"{contacts} new contacts"
            ),
        }

    def _digest_subject(self, content: dict, period: str) -> str:
        """Generate digest email subject."""
        period_label = {"morning": "Morning", "afternoon": "Midday", "evening": "Evening", "daily": "Daily"}
        label = period_label.get(period, "Daily")
        high = content["new_high_leads"]
        posts = content["new_posts"]

        if high > 0:
            return f"🔔 Medicilon BD Intelligence — {label} Digest ({high} high-priority leads)"
        elif posts > 0:
            return f"Medicilon BD Intelligence — {label} Digest ({posts} LinkedIn matches)"
        else:
            return f"Medicilon BD Intelligence — {label} Digest"

    def _build_digest_html(self, content: dict, period: str) -> str:
        """Build HTML email digest."""
        period_label = {"morning": "Morning", "afternoon": "Midday", "evening": "Evening", "daily": "Daily"}
        label = period_label.get(period, "Daily")

        top_posts_html = ""
        for p in content["top_posts"][:5]:
            score_color = "#27AE60" if p["relevance_score"] >= 70 else "#F5A623"
            top_posts_html += f"""
            <tr>
              <td style="padding:10px;border-bottom:1px solid #e0e0e0">
                <span style="font-size:11px;color:{score_color};font-weight:600">[{p['relevance_score']}]</span>
                <strong>{p['author_name'] or 'Unknown'}</strong>
                {f"<span style='font-size:11px;color:#2E75B6'> · {p['author_title']}</span>" if p.get('author_title') else ""}
                <div style="font-size:12px;color:#555;margin-top:4px">{(p['content'] or '')[:150]}</div>
                <div style="font-size:10px;color:#999;margin-top:2px">{p['matched_keywords'] or ''}</div>
              </td>
            </tr>"""

        return f"""
        <html>
        <body style="font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333">
          <div style="background:#1F3864;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="color:white;margin:0;font-size:20px">Medicilon BD Intelligence</h1>
            <p style="color:#BDD7EE;margin:4px 0 0;font-size:13px">{label} Digest — {datetime.now().strftime('%B %d, %Y')}</p>
          </div>

          <div style="background:#f8f9fa;padding:16px;border:1px solid #e0e0e0">
            <h3 style="color:#1F3864;margin:0 0 8px">📊 Summary</h3>
            <table cellpadding="0" cellspacing="0" style="width:100%">
              <tr>
                <td style="padding:8px;text-align:center;background:#fff;border-radius:6px;width:25%">
                  <div style="font-size:24px;font-weight:700;color:#2E75B6">{content['new_posts']}</div>
                  <div style="font-size:11px;color:#888">LinkedIn Posts</div>
                </td>
                <td style="padding:8px;text-align:center;background:#fff;border-radius:6px;width:25%">
                  <div style="font-size:24px;font-weight:700;color:#27AE60">{content['new_high_leads']}</div>
                  <div style="font-size:11px;color:#888">High Priority</div>
                </td>
                <td style="padding:8px;text-align:center;background:#fff;border-radius:6px;width:25%">
                  <div style="font-size:24px;font-weight:700;color:#8E44AD">{content['new_contacts']}</div>
                  <div style="font-size:11px;color:#888">New Contacts</div>
                </td>
                <td style="padding:8px;text-align:center;background:#fff;border-radius:6px;width:25%">
                  <div style="font-size:14px;font-weight:700;color:#E67E22">🤖 AI</div>
                  <div style="font-size:11px;color:#888">Scored</div>
                </td>
              </tr>
            </table>
          </div>

          {f'''
          <div style="padding:16px;border:1px solid #e0e0e0;border-top:none">
            <h3 style="color:#1F3864;margin:0 0 12px">🔥 Top LinkedIn Matches</h3>
            <table cellpadding="0" cellspacing="0" style="width:100%">
              {top_posts_html or '<tr><td style="padding:20px;text-align:center;color:#999;font-size:13px">No high-priority posts in this period</td></tr>'}
            </table>
          </div>
          ''' if content['top_posts'] else ""}

          <div style="background:#1F3864;padding:12px;border-radius:0 0 8px 8px;text-align:center">
            <a href="http://localhost:8000/#leads" style="color:#BDD7EE;font-size:12px;text-decoration:none">🔗 Open Lead Intelligence Dashboard →</a>
          </div>

          <p style="font-size:10px;color:#999;text-align:center;margin-top:12px">
            Sent by Medicilon CRO Intelligence Platform · Generated at {content['timestamp']}<br>
            <a href="http://localhost:8000/#settings" style="color:#999">Manage notification preferences</a>
          </p>
        </body>
        </html>
        """

    # ── Desktop Push Notifications ───────────────────────────────────────────

    def generate_desktop_notification(self, payload: dict) -> dict:
        """
        Generate a desktop push notification payload.
        The frontend handles the actual browser notification display.

        Returns a dict the frontend can use to call new Notification().
        """
        return {
            "title": "Medicilon Intelligence",
            "body": payload.get("message", "New BD intelligence available"),
            "icon": "/assets/icon.png",
            "tag": payload.get("lead_source_id", ""),
            "data": {
                "page": payload.get("link_page", "leads"),
                "source_id": payload.get("lead_source_id"),
            },
            "requireInteraction": payload.get("require_interaction", False),
        }

    def push_to_desktop(self, user_id: int, message: str, link_page: str = "leads") -> bool:
        """Store a desktop notification for the frontend to display."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT INTO notifications (user_id, message, link_page) VALUES (?, ?, ?)",
                (user_id, message, link_page),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[NotificationPipeline] Push error: {e}")
            return False
        finally:
            conn.close()

    # ── Scheduled Digest Jobs ───────────────────────────────────────────────

    def generate_daily_alerts(self, min_score: int = 70) -> List[dict]:
        """
        Generate alert notifications for all high-scoring leads.
        Called by the scheduler (cron or task runner).
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        # Get all users with notifications enabled
        users = conn.execute(
            """SELECT u.id, s.notif_email, s.notif_morning, s.notif_afternoon,
                      s.notif_evening, s.min_lead_score
               FROM users u LEFT JOIN settings s ON u.id = s.user_id"""
        ).fetchall()

        alerts_generated = 0

        for user in users:
            min_score_user = user["min_lead_score"] or min_score

            # Check for high-priority LinkedIn posts
            high_priority_posts = conn.execute(
                """SELECT COUNT(*) FROM linkedin_posts
                   WHERE relevance_score >= ? AND processed = 0""",
                (min_score_user,)
            ).fetchone()[0]

            if high_priority_posts > 0:
                self.push_to_desktop(
                    user["id"],
                    f"🔥 {high_priority_posts} high-priority LinkedIn posts waiting for review",
                    "linkedin",
                )
                alerts_generated += 1

            # Check for new contacts
            new_contacts = conn.execute(
                """SELECT COUNT(*) FROM linkedin_contacts
                   WHERE created_at >= ?""",
                ((datetime.now() - timedelta(days=1)).isoformat(),)
            ).fetchone()[0]

            if new_contacts > 0:
                self.push_to_desktop(
                    user["id"],
                    f"👤 {new_contacts} new decision-makers discovered on LinkedIn",
                    "linkedin",
                )
                alerts_generated += 1

        conn.close()
        return {"alerts_generated": alerts_generated}

    def run_morning_digest(self) -> dict:
        """Run morning digest for all users."""
        return self._run_period_digest("morning")

    def run_afternoon_digest(self) -> dict:
        """Run afternoon digest for all users."""
        return self._run_period_digest("afternoon")

    def run_evening_digest(self) -> dict:
        """Run evening digest for all users."""
        return self._run_period_digest("evening")

    def _run_period_digest(self, period: str) -> dict:
        """Run digest for a specific period, sending to users who have it enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        field = f"notif_{period}"
        users = conn.execute(
            f"""SELECT u.id, u.email, s.notif_email, s.{field} as enabled
                FROM users u LEFT JOIN settings s ON u.id = s.user_id
                WHERE s.{field} = 1 OR s.{field} IS NULL"""
        ).fetchall()
        conn.close()

        results = []
        for user in users:
            email = user["notif_email"] or user["email"]
            if not email or not user["enabled"]:
                continue

            if period == "morning" and not user["enabled"]:
                continue

            result = self.send_email_digest(
                to_email=email,
                user_id=user["id"],
                period=period,
            )
            results.append({"user_id": user["id"], "email": email, **result})

        return {
            "period": period,
            "recipients": len(results),
            "sent": sum(1 for r in results if r.get("sent")),
            "results": results,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _log_notification(self, user_id: int, message: str):
        """Log a notification event to the database."""
        if user_id is None:
            return
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT INTO notifications (user_id, message, link_page) VALUES (?, ?, ?)",
                (user_id, message, "linkedin"),
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()


# ── Singleton ──────────────────────────────────────────────────────
pipeline = NotificationPipeline()
