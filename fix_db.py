import sqlite3

conn = sqlite3.connect('data/transactions.db')
conn.execute('DROP TABLE IF EXISTS transactions')
conn.execute("""
    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT DEFAULT 'Uncategorized',
        UNIQUE(date, description, amount)
    )
""")
conn.commit()
conn.close()
print('Table recreated with UNIQUE constraint')
