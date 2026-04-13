from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "neo4j+s://d2a5b462.databases.neo4j.io",
    auth=("neo4j", "E42fjl-1P6qr5-93ti0ckFCNDLQVvPZhbixzpl3CN7A")
)
try:
    driver.verify_connectivity()
    print("✅ Connected!")
except Exception as e:
    print(f"❌ Failed: {e}")
finally:
    driver.close()