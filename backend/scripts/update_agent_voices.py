import sqlite3

con = sqlite3.connect(r"d:\Final Project\Calling Agent\backend\calling_agent.db")
cur = con.cursor()
cur.execute("UPDATE agents SET voice_id = 'shreya' WHERE lower(name) LIKE '%shreya%'")
cur.execute("UPDATE agents SET voice_id = 'shubh' WHERE lower(name) LIKE '%yash%' OR lower(name) LIKE '%ai calling%'")
cur.execute("UPDATE agents SET voice_id = 'aditya' WHERE lower(name) LIKE '%aman%'")
cur.execute("UPDATE agents SET voice_id = 'shubh' WHERE voice_id LIKE 'dg_voice_%' OR voice_id IS NULL")
con.commit()

print("Updated agents:")
for row in cur.execute("SELECT id, name, voice_id FROM agents").fetchall():
    print(row)
con.close()
