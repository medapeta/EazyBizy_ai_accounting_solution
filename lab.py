# from flask import Flask, flash, redirect, render_template, request, session, url_for, make_response
# from flask_session import Session
# from sqlalchemy import create_engine, func, extract
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.exc import SQLAlchemyError
# from datetime import datetime
# from models import users_db, transactions_db, transaction_detail_db, chart_of_accounts_db, categories_db
# from werkzeug.security import generate_password_hash, check_password_hash
# from dotenv import load_dotenv
# import os
# from collections import defaultdict
# from helper import query_transaction_data ,get_profit_loss_data,get_balance_sheet_data , get_ledger_data,show_income_expense_chart, show_cash_chart,ask_deepseek
# from weasyprint import HTML

# ic,ex,tot = get_profit_loss_data()

# for i in ic:
#     formatted_input = "\n".join([f"{i}. {i['account_x'].name} - ${i['account_total']}" for i in ic])
#     print(formatted_input)    


import sqlite3

conn = sqlite3.connect("ai-bookeeping.db")
cursor = conn.cursor()

# Show table schema
cursor.execute("PRAGMA table_info(users_db);")
print("Table schema:")
for column in cursor.fetchall():
    print(column)

# Show all rows in users_db table
cursor.execute("SELECT * FROM users_db;")
rows = cursor.fetchall()

print("\nTable data:")
for row in rows:
    print(row)

conn.close()





# import sqlite3

# conn = sqlite3.connect("ai-bookeeping.db")
# cursor = conn.cursor()

# # List all tables
# cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
# tables = cursor.fetchall()

# print("Tables in database:")
# for table_name in tables:
#     table_name = table_name[0]
#     print(f"\n=== {table_name} ===")
    
#     try:
#         cursor.execute(f"SELECT * FROM {table_name}")
#         rows = cursor.fetchall()

#         # Print column names
#         cursor.execute(f"PRAGMA table_info({table_name});")
#         columns = [col[1] for col in cursor.fetchall()]
#         print(" | ".join(columns))

#         for row in rows:
#             print(row)
#     except Exception as e:
#         print(f"Error reading table {table_name}: {e}")

# conn.close()

# import sqlite3
# conn = sqlite3.connect("ai-bookeeping.db")
# cursor = conn.cursor()
# cursor.execute("PRAGMA table_info(users_db);")
# print(cursor.fetchall())
# conn.close()


# import sqlite3

# # Connect to your database
# conn = sqlite3.connect("ai-bookeeping.db")
# cursor = conn.cursor()

# # Add 'email' column to users_db table
# cursor.execute("ALTER TABLE users_db ADD COLUMN email TEXT;")

# # Confirm table structure
# cursor.execute("PRAGMA table_info(users_db);")
# for column in cursor.fetchall():
#     print(column)

# # Save changes and close connection
# conn.commit()
# conn.close()
