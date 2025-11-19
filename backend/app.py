import os
import argparse
from flask import Flask, jsonify, send_from_directory, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from collections import defaultdict
from models import SessionLocal, Issue, FileModification, init_db
from github_issues import collect_issues_data_rest
from github_file_fixes import collect_bugfix_files_local

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/")

def get_session():
    return SessionLocal()

# --- API Endpoints ---
@app.route("/api/bugs")
def api_bugs():
    session = get_session()
    items = session.query(Issue).order_by(Issue.created_at.desc()).limit(200).all()
    data = [i.to_dict() for i in items]
    session.close()
    return jsonify(data)

@app.route("/api/files")
def api_files():
    session = get_session()
    files = session.query(FileModification).order_by(FileModification.changes.desc()).limit(20).all()
    data = [{"file_name": f.file_name, "changes": f.changes} for f in files]
    session.close()
    return jsonify(data)

@app.route("/api/bugs/summary")
def api_bugs_summary():
    session = get_session()

    start_date_str = request.args.get('startDate')
    end_date_str = request.args.get('endDate')

    query = session.query(Issue).filter(Issue.state != "pull_request")

    if start_date_str:
        try:
            # Converte "2023-01-01" para objeto datetime
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(Issue.created_at >= start_date_obj)
        except ValueError:
            print(f"Formato de data inválido recebido: {start_date_str}")

        # 2. Tratamento da DATA FINAL
    if end_date_str:
        try:
            # Converte para objeto datetime
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d')

            # Ajusta para o final do dia (23:59:59) para pegar todos os bugs daquele dia
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)

            query = query.filter(Issue.created_at <= end_date_obj)
        except ValueError:
            print(f"Formato de data inválido recebido: {end_date_str}")

    bugs = query.all()
    bugs_over_time = defaultdict(int)
    time_to_fix = []
    dev_counts = defaultdict(int)

    for bug in bugs:
        if bug.created_at:
            day = bug.created_at.date().isoformat()
            bugs_over_time[day] += 1
        if bug.closed_at and bug.created_at:
            delta_days = (bug.closed_at - bug.created_at).days
            time_to_fix.append(delta_days)
        if bug.closed_by:
            dev_counts[bug.closed_by] += 1

    top_developers = sorted(
        [{"developer": k, "count": v} for k, v in dev_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:10]

    bugs_over_time_list = [{"period": k, "count": v} for k, v in sorted(bugs_over_time.items())]

    session.close()
    return jsonify({
        "bugs_over_time": bugs_over_time_list,
        "time_to_fix": time_to_fix,
        "top_developers": top_developers
    })

@app.route("/api/files/summary")
def api_files_summary():
    session = get_session()
    files = session.query(FileModification).order_by(FileModification.changes.desc()).limit(20).all()
    data = [{"file_name": f.file_name, "changes": f.changes} for f in files]
    session.close()
    return jsonify(data)

# --- Database Update ---
def update_database(max_issues=None, max_commits=None):
    print(f"[{datetime.now()}] Updating database...")
    try:
        collect_issues_data_rest(max_issues=max_issues)
        collect_bugfix_files_local(max_commits=max_commits)
        print(f"[{datetime.now()}] Update finished.")
    except Exception as e:
        print(f"[{datetime.now()}] Error during update: {e}")

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

# --- Scheduler ---
def start_scheduler():
    scheduler = BackgroundScheduler()
    # Scheduler will fetch all new data incrementally
    scheduler.add_job(lambda: update_database(max_issues=None, max_commits=None),
                      'interval', minutes=5, next_run_time=datetime.now())
    scheduler.start()
    print("Scheduler started.")

# --- Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-issues", type=int, default=200, help="Max issues to fetch on initial run")
    parser.add_argument("--max-commits", type=int, default=500, help="Max commits to fetch on initial run")
    args = parser.parse_args()

    init_db()
    # Initial run with limits
    update_database(max_issues=args.max_issues, max_commits=args.max_commits)
    start_scheduler()
    app.run(host="0.0.0.0", debug=True, use_reloader=False)
