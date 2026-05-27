"""
Notification Scheduler
Run as a cron job or scheduled task to:
1. Send morning/afternoon/evening email digests
2. Generate desktop push notifications
3. Clean up old notifications

Usage:
    python backend/scheduler.py morning
    python backend/scheduler.py afternoon
    python backend/scheduler.py evening
    python backend/scheduler.py generate-alerts
    python backend/scheduler.py cleanup
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.notification_pipeline import pipeline


def main():
    if len(sys.argv) < 2:
        print("Usage: python scheduler.py [morning|afternoon|evening|generate-alerts|cleanup|all]")
        sys.exit(1)

    command = sys.argv[1].lower()

    print(f"[Medicilon Scheduler] Running: {command}")
    print(f"  Time: {__import__('datetime').datetime.now().isoformat()}")

    if command == "aggregate":
        # Run LinkedIn intelligence aggregation
        from backend.services.linkedin_aggregator import aggregate_all, save_to_db, save_to_json
        try:
            leads = aggregate_all(max_total=80)
            inserted, contacts = save_to_db(leads)
            save_to_json(leads)
            tiers = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
            for l in leads:
                tiers[l["tier"]] = tiers.get(l["tier"], 0) + 1
            print(f"  Aggregation: {len(leads)} signals, {inserted} posts, {contacts} contacts")
            print(f"  Tiers: S={tiers['S']}, A={tiers['A']}, B={tiers['B']}, C={tiers['C']}, D={tiers['D']}")
        except Exception as e:
            print(f"  Aggregation failed: {e}")

    elif command == "morning":
        result = pipeline.run_morning_digest()
        print(f"  Morning digest: {result['sent']}/{result['recipients']} sent")

    elif command == "afternoon":
        result = pipeline.run_afternoon_digest()
        print(f"  Afternoon digest: {result['sent']}/{result['recipients']} sent")

    elif command == "evening":
        result = pipeline.run_evening_digest()
        print(f"  Evening digest: {result['sent']}/{result['recipients']} sent")

    elif command == "generate-alerts":
        result = pipeline.generate_daily_alerts()
        print(f"  Alerts generated: {result['alerts_generated']}")

    elif command == "cleanup":
        import sqlite3
        conn = sqlite3.connect(str(pipeline.db_path))
        # Delete notifications older than 30 days
        conn.execute(
            "DELETE FROM notifications WHERE created_at < datetime('now', '-30 days')"
        )
        # Mark old posts as processed
        conn.execute(
            "UPDATE linkedin_posts SET processed = 1 WHERE created_at < datetime('now', '-7 days')"
        )
        conn.commit()
        deleted = conn.total_changes
        conn.close()
        print(f"  Cleanup: {deleted} records removed")

    elif command == "all":
        print("  Running all scheduled tasks...")
        results = {}
        # Run aggregation first
        try:
            from backend.services.linkedin_aggregator import aggregate_all, save_to_db, save_to_json
            leads = aggregate_all(max_total=50)
            inserted, contacts = save_to_db(leads)
            save_to_json(leads)
            results["aggregate"] = f"{len(leads)} signals, {inserted} posts"
        except Exception as e:
            results["aggregate"] = f"FAILED: {e}"

        for cmd in ["morning", "afternoon", "evening", "generate-alerts", "cleanup"]:
            try:
                # Re-run for each command
                if cmd == "morning":
                    r = pipeline.run_morning_digest()
                    results[cmd] = f"Sent {r['sent']}/{r['recipients']}"
                elif cmd == "afternoon":
                    r = pipeline.run_afternoon_digest()
                    results[cmd] = f"Sent {r['sent']}/{r['recipients']}"
                elif cmd == "evening":
                    r = pipeline.run_evening_digest()
                    results[cmd] = f"Sent {r['sent']}/{r['recipients']}"
                elif cmd == "generate-alerts":
                    r = pipeline.generate_daily_alerts()
                    results[cmd] = f"{r['alerts_generated']} alerts"
                elif cmd == "cleanup":
                    import sqlite3
                    conn = sqlite3.connect(str(pipeline.db_path))
                    conn.execute("DELETE FROM notifications WHERE created_at < datetime('now', '-30 days')")
                    conn.execute("UPDATE linkedin_posts SET processed = 1 WHERE created_at < datetime('now', '-7 days')")
                    conn.commit()
                    results[cmd] = f"{conn.total_changes} records cleaned"
                    conn.close()
            except Exception as e:
                results[cmd] = f"FAILED: {e}"
        for k, v in results.items():
            print(f"  {k}: {v}")

    else:
        print(f"  Unknown command: {command}")
        sys.exit(1)

    print(f"[Medicilon Scheduler] Complete.")


if __name__ == "__main__":
    main()
