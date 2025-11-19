import os
import json
from dotenv import load_dotenv
from models import SessionLocal, upsert_issue, init_db, Base, engine
from datetime import datetime
import requests

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "facebook/react"
BUG_LABELS = ["Type: Bug"]
MAX_ISSUES = 20

HEADERS = {"Authorization": f"Bearer {TOKEN}"}
GRAPHQL_URL = "https://api.github.com/graphql"


def run_graphql_query(query, variables=None):
    resp = requests.post(
        GRAPHQL_URL,
        headers=HEADERS,
        json={"query": query, "variables": variables or {}},
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL query error: {data['errors']}")
    return data["data"]


def issue_to_dict(issue_node):
    # Skip pull requests
    if issue_node.get("pullRequest"):
        return None

    labels = [l["name"] for l in issue_node.get("labels", {}).get("nodes", [])]
    if not any(lbl in BUG_LABELS for lbl in labels):
        return None

    return {
        "id": int(issue_node["id"], 16) if isinstance(issue_node["id"], str) else issue_node["id"],
        "number": issue_node["number"],
        "title": issue_node["title"],
        "body": issue_node["body"],
        "state": issue_node["state"],
        "created_at": datetime.strptime(issue_node["createdAt"], "%Y-%m-%dT%H:%M:%SZ"),
        "closed_at": datetime.strptime(issue_node["closedAt"], "%Y-%m-%dT%H:%M:%SZ") if issue_node.get("closedAt") else None,
        "closed_by": issue_node.get("closedBy", {}).get("login"),
        "creator": issue_node["author"]["login"] if issue_node.get("author") else None,
        "comments_count": issue_node["comments"]["totalCount"],
        "labels": labels,
        "html_url": issue_node["url"],
        "repository": REPO_NAME,
    }


def clear_and_init_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating tables...")
    init_db()
    print("Database cleared and initialized.")


def collect_issues_data():
    session = SessionLocal()
    print(f"Collecting issues for {REPO_NAME} via GraphQL...")

    has_next_page = True
    cursor = None
    count = 0

    while has_next_page and count < MAX_ISSUES:
        query = """
        query($owner: String!, $name: String!, $after: String) {
          repository(owner: $owner, name: $name) {
            issues(first: 50, after: $after, states: [OPEN, CLOSED], labels: ["Type: Bug"], orderBy: {field: CREATED_AT, direction: DESC}) {
              edges {
                node {
                  id
                  number
                  title
                  body
                  state
                  createdAt
                  closedAt
                  closedBy { login }
                  author { login }
                  comments { totalCount }
                  labels(first: 20) { nodes { name } }
                  url
                  pullRequest { id }  # to detect PRs
                }
              }
              pageInfo { endCursor hasNextPage }
            }
          }
        }
        """

        variables = {
            "owner": REPO_NAME.split("/")[0],
            "name": REPO_NAME.split("/")[1],
            "after": cursor,
        }

        data = run_graphql_query(query, variables)
        issues_edges = data["repository"]["issues"]["edges"]
        page_info = data["repository"]["issues"]["pageInfo"]
        cursor = page_info["endCursor"]
        has_next_page = page_info["hasNextPage"]

        for edge in issues_edges:
            node = edge["node"]
            issue_data = issue_to_dict(node)
            if issue_data:
                upsert_issue(session, issue_data)
                count += 1
                if count >= MAX_ISSUES:
                    break

        session.commit()

    session.close()
    print(f"Inserted/updated {count} issues via GraphQL.")


if __name__ == "__main__":
    clear_and_init_db()
    collect_issues_data()
    print("Database populated with issues via GraphQL!")
