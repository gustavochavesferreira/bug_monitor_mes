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
MAX_PR = 20

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

def collect_file_changes():
    session = SessionLocal()
    repo = g.get_repo(REPO_NAME)
    file_counts = {}
    count = 0

    print("DEBUG: Starting to fetch closed PRs...")
    prs = repo.get_pulls(state="closed", sort="updated", direction="desc")
    print("DEBUG: PRs fetched, starting iteration...")

    for pr in prs:
        print(f"DEBUG: Checking PR #{pr.number}")
        if count >= MAX_PR:
            print("DEBUG: Reached MAX_PR limit")
            break

        if not pr.merged:
            print(f"DEBUG: PR #{pr.number} not merged, skipping")
            continue

        # Check linked issues
        linked_issues = []
        if pr.body:
            import re
            matches = re.findall(r"#(\d+)", pr.body)
            linked_issues = [int(m) for m in matches]

        bug_linked = False
        for issue_number in linked_issues:
            try:
                issue = repo.get_issue(issue_number)
                labels = [lbl.name for lbl in issue.labels]
                if any(lbl in BUG_LABELS for lbl in labels):
                    bug_linked = True
                    data = issue_to_dict(issue, repo.full_name)
                    if data:
                        upsert_issue(session, data)
            except Exception as e:
                print(f"DEBUG: Could not fetch issue #{issue_number}: {e}")

        if not bug_linked:
            print(f"DEBUG: PR #{pr.number} does not link to any bug-labeled issues, skipping")
            continue

        print(f"DEBUG: Processing PR #{pr.number}, linked to bug(s) {linked_issues}, changed files: {pr.changed_files}")
        for f in pr.get_files():
            file_counts[f.filename] = file_counts.get(f.filename, 0) + 1
            print(f"DEBUG: Counted file {f.filename}, total so far: {file_counts[f.filename]}")

        count += 1
        print(f"DEBUG: Processed {count} PRs so far")

    print("DEBUG: Finished iterating PRs, saving file modifications...")
    for fname, changes in file_counts.items():
        existing = session.query(FileModification).filter_by(repo=REPO_NAME, file_name=fname).one_or_none()
        if existing:
            existing.changes = changes
        else:
            session.add(FileModification(repo=REPO_NAME, file_name=fname, changes=changes))
        print(f"DEBUG: Saved file {fname} with {changes} changes")

    session.commit()
    session.close()
    print(f"DEBUG: File modification counts collected for {count} PRs")

if __name__ == "__main__":
    clear_and_init_db()
    #collect_issues_data()
    collect_file_changes()