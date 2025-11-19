import os
from git import Repo, GitCommandError
from models import SessionLocal, FileModification, Metadata
from datetime import datetime
import re

TARGET_REPO_URL = os.getenv("TARGET_REPO", "https://github.com/facebook/react.git")
LOCAL_REPO_PATH = "repos/react"
LOCAL_REPO_DIR = os.path.dirname(LOCAL_REPO_PATH)

import re

BUGFIX_KEYWORDS = [
    "fix", "fixes", "fixed",
    "bug", "bugs",
    "error", "errors",
    "issue", "issues",
    "patch", "hotfix",
    "regression"
]

# Issue-linking patterns
ISSUE_LINK_PATTERNS = [
    r"fixes\s+#\d+",
    r"fix\s+#\d+",
    r"closes\s+#\d+",
    r"closed\s+#\d+",
    r"resolve\s+#\d+",
    r"resolved\s+#\d+",
]

# Optional: exclude weak, noisy commits
EXCLUSION_PATTERNS = [
    r"fix typo",
    r"fix docs",
    r"fix documentation",
    r"fix formatting",
    r"update",
    r"refactor"
]

def is_bugfix_commit(msg: str) -> bool:
    """Return True if a commit message strongly indicates a bug fix."""

    # Normalize
    text = msg.lower()

    # Exclusions first
    for pattern in EXCLUSION_PATTERNS:
        if re.search(pattern, text):
            return False

    # Strong signal: issue reference
    for pattern in ISSUE_LINK_PATTERNS:
        if re.search(pattern, text):
            return True

    # Keyword search
    for word in BUGFIX_KEYWORDS:
        if word in text:
            return True

    return False

def clone_or_update_repo():
    os.makedirs(LOCAL_REPO_DIR, exist_ok=True)
    if not os.path.exists(LOCAL_REPO_PATH) or not os.path.isdir(os.path.join(LOCAL_REPO_PATH, ".git")):
        print(f"Cloning repo {TARGET_REPO_URL} ...")
        Repo.clone_from(TARGET_REPO_URL, LOCAL_REPO_PATH)
    else:
        print(f"Repo exists. Pulling latest changes ...")
        repo = Repo(LOCAL_REPO_PATH)
        try:
            repo.remotes.origin.pull()
        except GitCommandError as e:
            print(f"Warning: could not pull repo: {e}")

def collect_bugfix_files_local(max_commits=None):
    session = SessionLocal()
    clone_or_update_repo()
    repo = Repo(LOCAL_REPO_PATH)

    last_fetch_meta = session.query(Metadata).filter_by(key="last_file_fetch").one_or_none()
    last_fetch = datetime.fromisoformat(last_fetch_meta.value) if last_fetch_meta else None

    commits = list(repo.iter_commits('main'))

    if last_fetch:
        # Correct comparison using commit variable from the loop
        commits = [c for c in commits if datetime.fromtimestamp(c.committed_date) > last_fetch]

    if max_commits:
        commits = commits[:max_commits]

    print(f"Found {len(commits)} commits to analyze for bug fixes.")

    file_counts = {}
    for commit in commits:
        if is_bugfix_commit(commit.message):
            for f in commit.stats.files.keys():
                file_counts[f] = file_counts.get(f, 0) + 1

    print(f"Total bug-fix files found: {len(file_counts)}")

    for fname, changes in file_counts.items():
        existing = session.query(FileModification).filter_by(file_name=fname).one_or_none()
        if existing:
            existing.changes = changes
        else:
            session.add(FileModification(repo=TARGET_REPO_URL, file_name=fname, changes=changes))

    now_iso = datetime.now().isoformat()
    if last_fetch_meta:
        last_fetch_meta.value = now_iso
    else:
        session.add(Metadata(key="last_file_fetch", value=now_iso))

    session.commit()
    session.close()
    print("Bug-fix file collection complete.")
