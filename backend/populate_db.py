import os
import json
from datetime import datetime
from dotenv import load_dotenv
import requests
from models import SessionLocal, upsert_issue, init_db, Base, engine

load_dotenv()

# --- Configuration ---
TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    raise RuntimeError("GITHUB_TOKEN not set in .env")

REPO_NAME = "facebook/react"
BUG_LABELS = ["Type: Bug"]
MAX_ISSUES = 100  # adjust if you want more
PER_PAGE = 100  # GitHub REST max per page

HEADERS = {"Authorization": f"token {TOKEN}"}


# --- Helpers ---
def clear_and_init_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating tables...")
    init_db()
    print("Database cleared and initialized.")


def fetch_issue_details(issue_number):
    """Get full issue info (including closed_by) via REST API."""
    url = f"https://api.github.com/repos/{REPO_NAME}/issues/{issue_number}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def collect_issues_data_rest():
    session = SessionLocal()
    print(f"Collecting issues for {REPO_NAME} via REST API...")

    page = 1
    count = 0

    while True:
        params = {
            "state": "all",
            "labels": ",".join(BUG_LABELS),
            "per_page": PER_PAGE,
            "page": page,
        }

        resp = requests.get(
            f"https://api.github.com/repos/{REPO_NAME}/issues",
            headers=HEADERS,
            params=params,
        )
        resp.raise_for_status()
        issues = resp.json()
        if not issues:
            break

        for issue in issues:
            # Skip pull requests
            if "pull_request" in issue:
                continue

            # Fetch full issue details to get closed_by
            full_issue = fetch_issue_details(issue["number"])

            closed_by = full_issue.get("closed_by")
            issue_data = {
                "id": str(issue["id"]),
                "number": issue["number"],
                "title": issue["title"],
                "body": issue.get("body"),
                "state": issue["state"],
                "created_at": datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                "closed_at": datetime.strptime(full_issue["closed_at"], "%Y-%m-%dT%H:%M:%SZ")
                             if full_issue.get("closed_at") else None,
                "closed_by": closed_by["login"] if closed_by else None,
                "creator": issue.get("user", {}).get("login"),
                "comments_count": issue["comments"],
                "labels": [lbl["name"] for lbl in issue.get("labels", [])],
                "html_url": issue["html_url"],
                "repository": REPO_NAME,
            }

            upsert_issue(session, issue_data)
            count += 1

            if count >= MAX_ISSUES:
                break

        session.commit()
        if count >= MAX_ISSUES:
            break
        page += 1

    session.close()
    print(f"Inserted/updated {count} issues via REST API.")


# --- Main ---
if __name__ == "__main__":
    clear_and_init_db()
    collect_issues_data_rest()
    print("Database populated with issues via REST API!")
