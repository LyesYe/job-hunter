"""
Job Hunt Bot — daily XR / 3D / Computer Graphics job alerts to Discord.
Run manually:  python main.py
Run dry:       python main.py --dry-run
"""
import sys
from datetime import datetime
from src.scrapers import get_all_jobs
from src.database import load_seen_ids, save_seen_ids
from src.notifier import send_discord

DRY_RUN = "--dry-run" in sys.argv


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting job hunt...")
    if DRY_RUN:
        print("DRY RUN -- Discord notifications will NOT be sent, seen_jobs.json will NOT be updated")

    seen_ids = load_seen_ids()
    print(f"Already seen: {len(seen_ids)} jobs")

    all_jobs = get_all_jobs()
    print(f"\nTotal fetched: {len(all_jobs)} relevant jobs across all sources")

    new_jobs = [job for job in all_jobs if job["id"] not in seen_ids]
    print(f"New (unseen):  {len(new_jobs)} jobs\n")

    if DRY_RUN:
        for j in new_jobs:
            print(f"  [{j['source']:8}] {j['title']} — {j['company']} ({j['location']})")
        return

    send_discord(new_jobs)

    for job in new_jobs:
        seen_ids.add(job["id"])
    save_seen_ids(seen_ids)

    print(f"\nDone. Sent {len(new_jobs)} new alerts to Discord.")


if __name__ == "__main__":
    main()
