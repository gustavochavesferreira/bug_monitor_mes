import os
from git import Repo, GitCommandError
from models import SessionLocal, FileModification

TARGET_REPO_URL = os.getenv("TARGET_REPO", "https://github.com/facebook/react.git")
LOCAL_REPO_PATH = "repos/react"
LOCAL_REPO_DIR = os.path.dirname(LOCAL_REPO_PATH)

def clone_or_update_repo():
    # Ensure parent folder exists
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

def collect_bugfix_files_local(max_commits=2000):
    """
    Analyze commits to identify files most modified to fix bugs.
    Simple heuristic: commits containing "fix", "bug", or "error" in the message.
    """
    session = SessionLocal()

    # Make sure repo is up-to-date
    clone_or_update_repo()
    repo = Repo(LOCAL_REPO_PATH)

    file_counts = {}

    commits = list(repo.iter_commits('main', max_count=max_commits))
    for commit in commits:
        msg = commit.message.lower()
        print(msg)
        if "fix" in msg or "bug" in msg or "error" in msg:
            print(f"Commit {commit.hexsha}: {msg.strip()}")
            for f in commit.stats.files.keys():
                print(f"  Modified file: {f}")
                file_counts[f] = file_counts.get(f, 0) + 1
        print()

    print("Final file counts:", file_counts)

    # Save counts to database
    for fname, changes in file_counts.items():
        existing = session.query(FileModification).filter_by(file_name=fname).one_or_none()
        if existing:
            existing.changes = changes
        else:
            session.add(FileModification(repo=TARGET_REPO_URL, file_name=fname, changes=changes))

    session.commit()
    session.close()
    print(f"Collected file modifications for {len(file_counts)} files.")

if __name__ == "__main__":
    collect_bugfix_files_local()
    print("Database populated with most modified files!")