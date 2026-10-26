import sqlite3

conn = sqlite3.connect('backend/calling_agent.db')
c = conn.cursor()
c.execute("UPDATE agents SET tenant_id = '01500392-b288-47fe-885b-ff6867755b15' WHERE tenant_id IS NULL")
c.execute("UPDATE calls SET tenant_id = '01500392-b288-47fe-885b-ff6867755b15' WHERE tenant_id IS NULL")
conn.commit()

c.execute("SELECT id, name, tenant_id FROM agents")
agents = c.fetchall()
c.execute("SELECT count(*), count(tenant_id) FROM calls")
calls_cnt = c.fetchall()

print("Agents:", agents)
print("Calls:", calls_cnt)
conn.close()
