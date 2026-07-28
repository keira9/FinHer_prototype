import psycopg2
from datetime import date

# Connect to your database
conn = psycopg2.connect(
    dbname="FinHer",
    user="postgres",
    password="Ngabonziza@12345",  
    host="localhost",
    port="5432"
)
cur = conn.cursor()

def calculate_score(entrepreneur_id):
    # Transaction score
    cur.execute("""
        SELECT COUNT(*), AVG(amount) FROM mobilemoneytransaction
        WHERE entrepreneur_id = %s AND transaction_date >= CURRENT_DATE - INTERVAL '6 months'
    """, (entrepreneur_id,))
    count, avg_amount = cur.fetchone()
    count = count or 0
    avg_amount = avg_amount or 0
    transaction_score = min((count * 5) + (float(avg_amount) / 1000), 100)

    # Sacco score
    cur.execute("""
        SELECT join_date, contribution_amount FROM saccomembership
        WHERE entrepreneur_id = %s
    """, (entrepreneur_id,))
    result = cur.fetchone()
    sacco_score = 0
    if result:
        join_date, contribution = result
        months = (date.today().year - join_date.year) * 12 + (date.today().month - join_date.month)
        sacco_score = min((months * 2) + (float(contribution) / 100), 100)

    # Trade score
    cur.execute("""
        SELECT trade_frequency, trade_volume FROM informaltraderecord
        WHERE entrepreneur_id = %s
    """, (entrepreneur_id,))
    result = cur.fetchone()
    trade_score = 0
    if result:
        freq, volume = result
        trade_score = min((freq * 4) + (float(volume) / 500), 100)

    final_score = (transaction_score * 0.4) + (sacco_score * 0.35) + (trade_score * 0.25)

    # Save result
    cur.execute("""
        INSERT INTO creditscore (entrepreneur_id, transaction_score, sacco_score, trade_score, final_score)
        VALUES (%s, %s, %s, %s, %s)
    """, (entrepreneur_id, transaction_score, sacco_score, trade_score, final_score))
    conn.commit()

    return final_score

# Score all entrepreneurs
entrepreneur_ids = [1, 4, 5]

for eid in entrepreneur_ids:
    score = calculate_score(eid)
    print(f"Entrepreneur ID {eid}: Final Score = {score:.2f}")