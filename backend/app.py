# backend/app.py
import os
from flask import Flask, jsonify, send_from_directory
from models import SessionLocal, Issue
from datetime import datetime

# Dynamically locate the frontend folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))       
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "../frontend"))

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

    # bugs over time
    counts = {}
    for i in issues:
        m = i.created_at.strftime("%Y-%m") if i.created_at else None
        if m:
            counts[m] = counts.get(m, 0) + 1
    bugs_over_time = [{"period": k, "count": v} for k, v in sorted(counts.items())]

    # time to fix
    times = []
    for i in issues:
        if i.created_at and i.closed_at:
            dt = (i.closed_at - i.created_at).total_seconds() / 86400
            if dt >= 0:
                times.append(dt)

    # top developers
    dev = {}
    for i in issues:
        if i.closed_by:
            dev[i.closed_by] = dev.get(i.closed_by, 0) + 1
    top_devs = [{"developer": d, "count": c} for d, c in sorted(dev.items(), key=lambda x: -x[1])[:20]]

    session.close()
    return jsonify({
        "bugs_over_time": bugs_over_time,
        "time_to_fix": times[:1000],
        "top_developers": top_devs,
    })

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:p>")
def static_files(p):
    f = os.path.join(app.static_folder, p)
    if os.path.exists(f):
        return send_from_directory(app.static_folder, p)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(debug=True)