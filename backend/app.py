import os
from flask import Flask, jsonify, send_from_directory
from datetime import datetime
from models import SessionLocal, Issue, FileModification
from file_tracker import collect_bugfix_files_local
from populate_db import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/")

def get_session():
    return SessionLocal()

@app.route("/api/bugs")
def api_bugs():
    session = get_session()
    items = session.query(Issue).order_by(Issue.created_at.desc()).limit(200).all()
    data = [i.to_dict() for i in items]
    session.close()
    return jsonify(data)

@app.route("/api/bugs/summary")
def api_summary():
    session = get_session()
    issues = session.query(Issue).all()

    # Bugs over time
    counts = {}
    for i in issues:
        if i.created_at:
            key = i.created_at.strftime("%Y-%m")
            counts[key] = counts.get(key, 0) + 1
    bugs_over_time = [{"period": k, "count": v} for k, v in sorted(counts.items())]

    # Time to fix
    times = [
        (i.closed_at - i.created_at).total_seconds() / 86400
        for i in issues
        if i.created_at and i.closed_at and i.closed_at >= i.created_at
    ]

    # Top developers
    dev_counts = {}
    for i in issues:
        if i.closed_by:
            dev_counts[i.closed_by] = dev_counts.get(i.closed_by, 0) + 1
    top_devs = sorted(
        [{"developer": d, "count": c} for d, c in dev_counts.items()],
        key=lambda x: -x["count"]
    )[:20]

    session.close()
    return jsonify({
        "bugs_over_time": bugs_over_time,
        "time_to_fix": times[:1000],
        "top_developers": top_devs,
    })

@app.route("/api/files")
def api_files():
    session = get_session()
    files = session.query(FileModification).order_by(FileModification.changes.desc()).limit(20).all()
    data = [{"file_name": f.file_name, "changes": f.changes} for f in files]
    session.close()
    return jsonify(data)

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:p>")
def static_files(p):
    file_path = os.path.join(app.static_folder, p)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, p)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, use_reloader=True)
