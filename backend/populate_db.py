import os
from dotenv import load_dotenv
from github import Github, Auth
from models import SessionLocal, upsert_issue, FileModification, init_db, Base, engine
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "facebook/react"
BUG_LABELS = ["Type: Bug"]
MAX_ISSUES = 20

g = Github(auth=Auth.Token(TOKEN), per_page=100)

def issue_to_dict(issue, repo_full_name):
    if getattr(issue, "pull_request", None):
        return None

    labels = [lbl.name for lbl in issue.labels]
    if not any(lbl in BUG_LABELS for lbl in labels):
        return None

    return {
        "id": issue.id,
        "number": issue.number,
        "title": issue.title,
        "body": issue.body,
        "state": issue.state,
        "created_at": issue.created_at,
        "closed_at": issue.closed_at,
        "closed_by": issue.closed_by.login if issue.closed_by else None,
        "creator": issue.user.login,
        "comments_count": issue.comments,
        "labels": labels,
        "html_url": issue.html_url,
        "repository": repo_full_name,
    }

def clear_and_init_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating tables...")
    init_db()
    print("Database cleared and initialized.")

def collect_issues_data():
    session = SessionLocal()
    repo = g.get_repo(REPO_NAME)
    issues = repo.get_issues(state="all", labels=BUG_LABELS)

    count = 0
    for issue in issues:
        if count >= MAX_ISSUES:
            break

        data = issue_to_dict(issue, repo.full_name)
        if not data:
            continue

        upsert_issue(session, data)
        count += 1

        if count % 50 == 0:
            session.commit()

    session.commit()
    session.close()
    print(f"Inserted/updated {count} issues.")

if __name__ == "__main__":
    clear_and_init_db()
    collect_issues_data()
    print("Database populated with issues!")
