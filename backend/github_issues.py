import os
import json
import requests
from datetime import datetime
from models import SessionLocal, upsert_issue, Metadata
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "facebook/react"
BUG_LABELS = ["Type: Bug"]
PER_PAGE = 100
HEADERS = {"Authorization": f"token {TOKEN}"}

def fetch_issue_details(issue_number):
    url = f"https://api.github.com/repos/{REPO_NAME}/issues/{issue_number}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

def collect_issues_data_rest(max_issues=None):
    session = SessionLocal()
    meta = session.query(Metadata).filter_by(key="last_issue_fetch").one_or_none()
    last_fetch = meta.value if meta else None

    count = 0
    page = 1

    while True:
        params = {
            "state": "all",
            "labels": ",".join(BUG_LABELS),
            "per_page": PER_PAGE,
            "page": page
        }
        if last_fetch:
            params["since"] = last_fetch

        resp = requests.get(f"https://api.github.com/repos/{REPO_NAME}/issues", headers=HEADERS, params=params)
        resp.raise_for_status()
        issues = resp.json()
        if not issues:
            break

        for issue in issues:
            if "pull_request" in issue:
                continue
            full = fetch_issue_details(issue["number"])
            data = {
                "id": str(full["id"]),
                "number": full["number"],
                "title": full["title"],
                "body": full.get("body"),
                "state": full["state"],
                "created_at": datetime.fromisoformat(full["created_at"].replace("Z", "+00:00")) if full.get("created_at") else None,
                "closed_at": datetime.fromisoformat(full["closed_at"].replace("Z", "+00:00")) if full.get("closed_at") else None,
                "closed_by": full.get("closed_by", {}).get("login") if full.get("closed_by") else None,
                "creator": full["user"]["login"] if full.get("user") else None,
                "comments_count": full.get("comments", 0),
                "labels": [l["name"] for l in full.get("labels", [])],
                "html_url": full.get("html_url"),
                "repository": REPO_NAME
            }
            upsert_issue(session, data)
            count += 1
            if max_issues and count >= max_issues:
                break

        session.commit()
        page += 1
        if max_issues and count >= max_issues:
            break

    # Update last fetch timestamp
    now_iso = datetime.now().isoformat()
    if meta:
        meta.value = now_iso
    else:
        session.add(Metadata(key="last_issue_fetch", value=now_iso))
    session.commit()
    session.close()
    print(f"Upserted {count} issues.")
