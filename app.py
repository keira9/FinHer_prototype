from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

import joblib
model = joblib.load("finher_model.pkl")
scaler = joblib.load("finher_scaler.pkl")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "finher_secret_key_change_this")

import os

def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    else:
        return psycopg2.connect(
            dbname="FinHer",
            user="postgres",
            password="Ngabonziza@12345",
            host="localhost",
            port="5432"
        )

def calculate_score(entrepreneur_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*), AVG(amount) FROM mobilemoneytransaction
        WHERE entrepreneur_id = %s AND transaction_date >= CURRENT_DATE - INTERVAL '6 months'
    """, (entrepreneur_id,))
    count, avg_amount = cur.fetchone()
    count = count or 0
    avg_amount = float(avg_amount or 0)

    cur.execute("""
        SELECT join_date, contribution_amount FROM saccomembership
        WHERE entrepreneur_id = %s
    """, (entrepreneur_id,))
    result = cur.fetchone()
    sacco_months, sacco_contribution = 0, 0
    if result:
        join_date, contribution = result
        sacco_months = (date.today().year - join_date.year) * 12 + (date.today().month - join_date.month)
        sacco_contribution = float(contribution)

    cur.execute("""
        SELECT trade_frequency, trade_volume FROM informaltraderecord
        WHERE entrepreneur_id = %s
    """, (entrepreneur_id,))
    result = cur.fetchone()
    trade_frequency, trade_volume = 0, 0
    if result:
        trade_frequency, trade_volume = result[0], float(result[1])

    features = [[count, avg_amount, sacco_months, sacco_contribution, trade_frequency, trade_volume]]
    features_scaled = scaler.transform(features)
    probability = model.predict_proba(features_scaled)[0][1]
    final_score = round(probability * 850, 2)

    cur.close()
    conn.close()

    return {
        "transaction_score": count,
        "sacco_score": sacco_months,
        "trade_score": trade_frequency,
        "final_score": final_score,
        "probability": round(probability * 100, 1)
    }

@app.route("/", methods=["GET"])
def home():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password_hash = generate_password_hash(password)

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash)
            )
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            cur.close()
            conn.close()
            return render_template("signup.html", error="Username already exists.")
        cur.close()
        conn.close()
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result and check_password_hash(result[0], password):
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/decide/<int:eid>/<decision>")
def make_decision(eid, decision):
    if "username" not in session:
        return redirect(url_for("login"))

    if decision not in ["Approved", "Rejected", "Deferred"]:
        return "Invalid decision", 400

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT is_admin FROM users WHERE username = %s", (session["username"],))
    result = cur.fetchone()
    if result and result[0]:
        cur.close()
        conn.close()
        return "System Admins cannot make credit decisions — this action is reserved for Lender Admins.", 403

    cur.execute(
        "INSERT INTO creditdecision (entrepreneur_id, decision, decided_by) VALUES (%s, %s, %s)",
        (eid, decision, session["username"])
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("entrepreneur_detail", eid=eid))

@app.route("/register-borrower", methods=["GET", "POST"])
def register_borrower():
    if request.method == "POST":
        full_name = request.form["full_name"]
        phone = request.form["phone"]
        location = request.form["location"]
        business_type = request.form["business_type"]
        business_start_date = request.form["business_start_date"]

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO entrepreneur (full_name, phone_number, location, business_type, business_start_date)
                VALUES (%s, %s, %s, %s, %s) RETURNING entrepreneur_id
            """, (full_name, phone, location, business_type, business_start_date))
            new_eid = cur.fetchone()[0]
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            cur.close()
            conn.close()
            return render_template("register_borrower.html", error="This phone number is already registered.")
        cur.close()
        conn.close()

        return redirect(url_for("add_activity", eid=new_eid))

    return render_template("register_borrower.html")


@app.route("/add-activity/<int:eid>", methods=["GET", "POST"])
def add_activity(eid):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        amount = request.form.get("amount")
        sacco_name = request.form.get("sacco_name")
        sacco_join_date = request.form.get("sacco_join_date")
        contribution = request.form.get("contribution")
        trade_volume = request.form.get("trade_volume")
        trade_frequency = request.form.get("trade_frequency")

        if amount:
            cur.execute("""
                INSERT INTO mobilemoneytransaction (entrepreneur_id, transaction_type, amount, transaction_date, frequency_flag)
                VALUES (%s, 'deposit', %s, CURRENT_DATE, 1)
            """, (eid, amount))

        if sacco_name and sacco_join_date and contribution:
            cur.execute("""
                INSERT INTO saccomembership (entrepreneur_id, sacco_name, join_date, contribution_amount, membership_status)
                VALUES (%s, %s, %s, %s, 'active')
            """, (eid, sacco_name, sacco_join_date, contribution))

        if trade_volume and trade_frequency:
            cur.execute("""
                INSERT INTO informaltraderecord (entrepreneur_id, trade_volume, trade_frequency, market_location, record_date)
                VALUES (%s, %s, %s, 'Self-reported', CURRENT_DATE)
            """, (eid, trade_volume, trade_frequency))

        conn.commit()

    cur.execute("SELECT full_name FROM entrepreneur WHERE entrepreneur_id = %s", (eid,))
    name = cur.fetchone()[0]
    cur.close()
    conn.close()

    score = calculate_score(eid)

    return render_template("add_activity.html", eid=eid, name=name, score=score)

@app.route("/check-score", methods=["GET", "POST"])
def check_score():
    result = None
    error = None

    if request.method == "POST":
        phone = request.form["phone"]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT entrepreneur_id, full_name, location, business_type
            FROM entrepreneur WHERE phone_number = %s
        """, (phone,))
        entrepreneur = cur.fetchone()
        cur.close()
        conn.close()

        if entrepreneur:
            eid = entrepreneur[0]
            score = calculate_score(eid)
            result = {
                "eid": eid,
                "name": entrepreneur[1],
                "location": entrepreneur[2],
                "business_type": entrepreneur[3],
                "score": score
            }
        else:
            error = "No profile found with that phone number. Please check and try again."

    return render_template("check_score.html", result=result, error=error)


@app.route("/apply/<int:eid>")
def apply_for_loan(eid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO loanapplication (entrepreneur_id, status) VALUES (%s, 'Submitted')",
        (eid,)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("check_score") + f"?applied={eid}")

@app.route("/fairness-check")
def fairness_check():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT is_admin FROM users WHERE username = %s", (session["username"],))
    result = cur.fetchone()
    if not result or not result[0]:
        cur.close()
        conn.close()
        return "Access denied: Admins only.", 403

    cur.execute("SELECT entrepreneur_id, location FROM entrepreneur")
    entrepreneurs = cur.fetchall()
    cur.close()
    conn.close()

    location_scores = {}
    for eid, location in entrepreneurs:
        score = calculate_score(eid)["final_score"]
        location_scores.setdefault(location, []).append(score)

    fairness_data = []
    for location, scores in location_scores.items():
        avg_score = round(sum(scores) / len(scores), 2)
        fairness_data.append({
            "location": location,
            "count": len(scores),
            "avg_score": avg_score
        })
    fairness_data.sort(key=lambda x: x["avg_score"], reverse=True)
    overall_avg = round(sum(s["avg_score"] * s["count"] for s in fairness_data) / sum(s["count"] for s in fairness_data), 2)

    return render_template("fairness.html", fairness_data=fairness_data, overall_avg=overall_avg)
@app.route("/api/score/<int:eid>")
def api_score(eid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT full_name, location, business_type FROM entrepreneur WHERE entrepreneur_id = %s", (eid,))
    entrepreneur = cur.fetchone()
    cur.close()
    conn.close()

    if not entrepreneur:
        return {"error": "Applicant not found"}, 404

    score = calculate_score(eid)
    band = 'Excellent' if score["final_score"] >= 700 else ('Good' if score["final_score"] >= 550 else ('Fair' if score["final_score"] >= 400 else 'Poor'))

    return {
        "applicant_id": eid,
        "full_name": entrepreneur[0],
        "location": entrepreneur[1],
        "business_type": entrepreneur[2],
        "finher_score": score["final_score"],
        "score_band": band,
        "score_breakdown": {
            "mobile_money_transactions": score["transaction_score"],
            "sacco_membership_months": score["sacco_score"],
            "informal_trade_frequency": score["trade_score"]
        }
    }

@app.route("/admin")
def admin():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT is_admin FROM users WHERE username = %s", (session["username"],))
    result = cur.fetchone()
    if not result or not result[0]:
        cur.close()
        conn.close()
        return "Access denied: Admins only.", 403

    cur.execute("SELECT user_id, username, is_admin FROM users ORDER BY user_id")
    users = cur.fetchall()

    cur.execute("""
        SELECT cs.score_id, e.full_name, cs.final_score, cs.calculated_date
        FROM creditscore cs
        JOIN entrepreneur e ON cs.entrepreneur_id = e.entrepreneur_id
        ORDER BY cs.calculated_date DESC
        LIMIT 20
    """)
    audit_log = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin.html", users=users, audit_log=audit_log)

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT is_admin FROM users WHERE username = %s", (session["username"],))
    admin_result = cur.fetchone()
    is_admin = admin_result[0] if admin_result else False

    cur.execute("SELECT entrepreneur_id, full_name, location, business_type FROM entrepreneur")
    entrepreneurs = cur.fetchall()

    data = []
    for e in entrepreneurs:
        eid, name, location, biz_type = e
        score = calculate_score(eid)

        cur.execute("""
            SELECT decision FROM creditdecision
            WHERE entrepreneur_id = %s ORDER BY decided_at DESC LIMIT 1
        """, (eid,))
        decision_result = cur.fetchone()
        decision = decision_result[0] if decision_result else "Pending"

        data.append({
            "id": eid,
            "name": name,
            "location": location,
            "business_type": biz_type,
            "final_score": score["final_score"],
            "decision": decision
        })

    cur.close()
    conn.close()

    return render_template("dashboard.html", entrepreneurs=data, username=session["username"], is_admin=is_admin)

@app.route("/entrepreneur/<int:eid>")
def entrepreneur_detail(eid):
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT full_name, location, business_type FROM entrepreneur WHERE entrepreneur_id = %s", (eid,))
    entrepreneur = cur.fetchone()

    cur.execute("""
        SELECT decision, decided_by, decided_at FROM creditdecision
        WHERE entrepreneur_id = %s ORDER BY decided_at DESC LIMIT 1
    """, (eid,))
    latest_decision = cur.fetchone()

    cur.close()
    conn.close()

    score = calculate_score(eid)

    return render_template("detail.html", entrepreneur=entrepreneur, score=score, eid=eid, latest_decision=latest_decision)

if __name__ == "__main__":
    app.run(debug=True)