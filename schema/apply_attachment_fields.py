#!/usr/bin/env python3
"""
Add attachment fields to emails table
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def apply_attachment_fields():
    db_url = os.getenv('DATABASE_URL').strip('"')
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    with open('schema/add_attachment_fields.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    
    cur.execute(sql)
    conn.commit()
    
    # Verify columns added
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'emails' 
        AND column_name IN ('attachment_file_path', 'attachment_image_path')
        ORDER BY column_name
    """)
    
    columns = cur.fetchall()
    print("\n✓ Attachment fields in emails table:")
    for col in columns:
        print(f"  - {col[0]}")
    
    cur.close()
    conn.close()
    print("\n✓ Attachment fields added successfully!")

if __name__ == "__main__":
    apply_attachment_fields()
