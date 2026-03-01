import psycopg2

conn = psycopg2.connect('postgresql://postgres:Teeli%40322@localhost/FinMatcher')
cur = conn.cursor()

cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='processed_emails' 
    ORDER BY ordinal_position
""")

cols = cur.fetchall()
print('\n📋 Columns in processed_emails table:')
for c in cols:
    print(f'  - {c[0]}')

conn.close()
