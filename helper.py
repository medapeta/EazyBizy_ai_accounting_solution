from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify, make_response
from flask_session import Session
from sqlalchemy import create_engine, func, extract
from sqlalchemy.orm import sessionmaker,joinedload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from models import users_db, transactions_db, transaction_detail_db, chart_of_accounts_db
from dotenv import load_dotenv
import os
from collections import defaultdict
import requests
from functools import wraps


load_dotenv()  # Load from .env file

engine = create_engine('sqlite:///ai-bookeeping.db')
Session = sessionmaker(bind=engine)
db_session = Session()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))  # Adjust to your login route name
        return f(*args, **kwargs)
    return decorated_function


def query_transaction_data():
    results = (
            db_session.query(transaction_detail_db)
            .join(transaction_detail_db.transaction)   # join to transactions_db
            .join(transaction_detail_db.account)       # join to chart_of_accounts_db
            .filter(transactions_db.user_id == session["user_id"])  # filter on parent transaction's user
            .all()
            )
    
    # Group all lines by account
    grouped_lines = defaultdict(list)
    for line in results:
        grouped_lines[line.account].append(line)

    return grouped_lines

def get_profit_loss_data():

    income = []
    expense = []
    group_accounts = query_transaction_data()

    for acct, trxs in group_accounts.items():
        if acct.type in ('Revenue','Expense'):
            accounts = {}
            accounts["account_x"] = acct # we need the name, type of the account

            # now let's grap the account totals amounts 
            total = []
            for transaction in trxs:
                if acct.normal_side == "debit":
                    if transaction.is_debit:
                        total.append(transaction.amount)
                    else: #if the transaction is credited while normal_side being debit
                        total.append(-(transaction.amount))
                elif acct.normal_side == "credit":
                    if transaction.is_debit: #if the transaction is credited while normal_side being debit
                        total.append(-(transaction.amount))
                    else: 
                        total.append(transaction.amount)
            accounts["account_total"] = sum(total)
            if acct.type == 'Revenue':
                income.append(accounts)
            if acct.type == 'Expense':
                expense.append(accounts)
    
    # taking total off all incomes and total expenses
    
    total_incomes = []
    total_expenses = []
    for acc in income:
        total_incomes.append(acc["account_total"])
    for acc in expense:
        total_expenses.append(acc["account_total"])
    total_ie = {
    "incomes": sum(total_incomes) if total_incomes else 0,
    "expenses": sum(total_expenses) if total_expenses else 0,
    "net": (sum(total_incomes)-sum(total_expenses))
    }

    return income, expense, total_ie


def get_balance_sheet_data():
    
    asset = []
    liability = []
    equity = []
    
    names = []
    group_accounts = query_transaction_data()

    for acct, trxs in group_accounts.items():
        if acct.type in ('Asset','Liability','Equity'):
            names.append(acct.name)
            accounts = {}
            accounts["account_x"] = acct # we need the name, type of the account

            # now let's grap the account totals amounts 
            total = []
            for transaction in trxs:
                if acct.normal_side == "debit":
                    if transaction.is_debit:
                        total.append(transaction.amount)
                    else: #if the transaction is credited while normal_side being debit
                        total.append(-(transaction.amount))
                elif acct.normal_side == "credit":
                    if transaction.is_debit: #if the transaction is credited while normal_side being debit
                        total.append(-(transaction.amount))
                    else: 
                        total.append(transaction.amount)
            accounts["account_total"] = sum(total)
            if acct.type == 'Asset':
                asset.append(accounts)
            if acct.type == 'Liability':
                liability.append(accounts)
            if acct.type == 'Equity':
                equity.append(accounts)

    # taking care accounts that are not in journal to count them in bs
    accounts_z = db_session.query(chart_of_accounts_db).filter_by(user_id=session["user_id"])

    for row in accounts_z:

        if row.type in ('Asset','Liability','Equity') and row.name not in names:
            accounts = {}
            accounts["account_x"] = row
            accounts["account_total"] = row.opening_balance
            if row.type == 'Asset':
                asset.append(accounts)
            if row.type == 'Liability':
                liability.append(accounts)
            if row.type == 'Equity':
                equity.append(accounts)
       

    # taking total off all asset, liability, capital
    total_asset = []
    total_liability = []
    total_equity = []
    for acc in asset:
        total_asset.append(acc["account_total"])
    for acc in liability:
        total_liability.append(acc["account_total"])
    for acc in equity:
        total_equity.append(acc["account_total"])
    total_bs = {
    "assets": sum(total_asset) if total_asset else 0,
    "liabilities": sum(total_liability) if total_liability else 0,
    "equity": sum(total_equity) if total_equity else 0,
    }

    return asset, liability, equity, total_bs


def get_ledger_data():         

    grouped_lines = query_transaction_data()

    for_ledger_accounts = []
    for_cash_tracking = {}
    # Now process each account's lines
    for account, lines in grouped_lines.items():
        entry = {
            "account_x": account,
            "lines": lines,
            "balances": []
        }

        balances = [account.opening_balance]
        balance_dates = [account.created_at] #for cash tracking purposes only
        for line in lines:
            last_balance = balances[-1]
            if account.normal_side == 'debit':
                if line.is_debit:
                    balances.append(last_balance + line.amount)
                    balance_dates.append(line.transaction.date)
                else:
                    balances.append(last_balance - line.amount)
                    balance_dates.append(line.transaction.date)
            else:  # normal_side == 'credit'
                if line.is_debit:
                    balances.append(last_balance - line.amount)
                    balance_dates.append(line.transaction.date)
                else:
                    balances.append(last_balance + line.amount)
                    balance_dates.append(line.transaction.date)
        if account.name.lower() == 'cash':
            for_cash_tracking["balances"] = balances
            for_cash_tracking["dates"] = balance_dates
         
        entry["balances"] = balances[1:]  # Skip the opening balance in the list
        
        for_ledger_accounts.append(entry)

    return for_ledger_accounts, for_cash_tracking #this returns each account with their respective transaction lines and balances after each transaction

# showing charts
def show_income_expense_chart():
     *_, total_ie = get_profit_loss_data()
     income = total_ie["incomes"]
     expense = total_ie["expenses"]

     return income,expense

def show_cash_chart():
    *_, cash_tracking = get_ledger_data()
    if "balances" not in cash_tracking:
        # Log or handle error or initialize
        cash_tracking["balances"] = []
    balances = cash_tracking["balances"]
    if "dates" not in cash_tracking:
        # Log or handle error or initialize
        cash_tracking["dates"] = []
    balance_date = cash_tracking["dates"]
    dates = []
    for d in balance_date:
        formatted = d.strftime("%b-%d-%y")  # -> 'Jun-01-25'
        dates.append(formatted)

    return balances, dates


def ask_deepseek(user_message,system_c):
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        raise ValueError("DeepSeek API key not found in environment variables")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000", 
        "X-Title": "EazyBizy"  
    }

    data = {
        "model": "deepseek/deepseek-r1-distill-llama-70b:free",
        "messages": [
            {"role": "system", "content": system_c},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.3,  # Low for consistent categorization,
        "max_tokens": 700
    }
    try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
            response.raise_for_status()  # Raise error for non-2xx codes

            json_data = response.json()
            return json_data["choices"][0]["message"]["content"]

    except Exception as e:
        print("AI API error:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Response content:", e.response.text)
        return "Sorry, something went wrong with the AI."

# formating profit loss statement for ai analysis
def format_pl_data():
    income, expense, total_ie = get_profit_loss_data()
    lines = ["Profit and Loss Summary:\n"]

    lines.append("Income:")
    for inc in income:
        lines.append(f"- {inc['account_x'].name}: {inc['account_total']:.2f}")

    lines.append("\nExpenses:")
    for exp in expense:
        lines.append(f"- {exp['account_x'].name}: {exp['account_total']:.2f}")

    lines.append(f"\nTotal Income: {total_ie['incomes']:.2f}")
    lines.append(f"Total Expenses: {total_ie['expenses']:.2f}")
    lines.append(f"Net Profit/Loss: {total_ie['net']:.2f}")

    return "\n".join(lines)

def format_balance_sheet_data_for_ai():
    from decimal import Decimal

    grouped_lines = query_transaction_data()

    all_accounts = db_session.query(chart_of_accounts_db)\
        .filter_by(user_id=session["user_id"])\
        .options(joinedload(chart_of_accounts_db.transaction_lines))\
        .order_by(chart_of_accounts_db.type, chart_of_accounts_db.name)\
        .all()
    transactions_by_account = {acct.id: txns for acct, txns in grouped_lines.items()}

    assets, liabilities, equity = [], [], []
    total_assets = total_liabilities = total_equity = Decimal("0.00")

    # Compute balances for all accounts
    for acct in all_accounts:
        balance = acct.opening_balance or Decimal("0.00")
        txns = transactions_by_account.get(acct.id, [])
        for txn in txns:
            if acct.normal_side == 'debit':
                balance += txn.amount if txn.is_debit else -txn.amount
            else:
                balance += -txn.amount if txn.is_debit else txn.amount

        entry = {
            "account_x": acct,
            "account_total": balance
        }

        if acct.type == 'Asset':
            assets.append(entry)
            total_assets += balance
        elif acct.type == 'Liability':
            liabilities.append(entry)
            total_liabilities += balance
        elif acct.type == 'Equity':
            equity.append(entry)
            total_equity += balance  # This is just raw equity

    # Add Net Income to Equity
    *_, total_ie = get_profit_loss_data()
    net_income = Decimal(total_ie["net"])
    equity.append({
        "account_x": chart_of_accounts_db(
            name="Current Year Earnings" if net_income >= 0 else "Current Period Loss",
            code="399",
            type="Equity",
            normal_side="credit" if net_income >= 0 else "debit",
            opening_balance=0,
            user_id=session["user_id"]
        ),
        "account_total": abs(net_income)
    })
    total_equity += net_income

    # Add Owner's Capital to Equity
    capital_account_name = f"{session.get('bussiness_name', 'Business')} Capital"
    capital_balance = Decimal("0.00")
    for acct in all_accounts:
        if acct.type == 'Equity' and capital_account_name in acct.name:
            capital_balance = acct.opening_balance or Decimal("0.00")
            txns = transactions_by_account.get(acct.id, [])
            for txn in txns:
                if acct.normal_side == 'debit':
                    capital_balance += txn.amount if txn.is_debit else -txn.amount
                else:
                    capital_balance += -txn.amount if txn.is_debit else txn.amount
            break

    equity.append({
        "account_x": chart_of_accounts_db(
            name=capital_account_name,
            code="300",
            type="Equity",
            normal_side="credit",
            opening_balance=0,
            user_id=session["user_id"]
        ),
        "account_total": capital_balance
    })
    total_equity += capital_balance

    total_liability_equity = total_liabilities + total_equity

    # Format output for AI
    def format_accounts(label, accounts_list):
        formatted_lines = [f"\n**{label.upper()}**"]
        for entry in accounts_list:
            acc = entry["account_x"]
            total = entry["account_total"]
            formatted_lines.append(f"- **{acc.name}** ({acc.type}): ${total:,.2f}")
        return "\n".join(formatted_lines)

    summary = [
        "**BALANCE SHEET SUMMARY**",
        "============================",
        format_accounts("Assets", assets),
        format_accounts("Liabilities", liabilities),
        format_accounts("Equity", equity),
        "\n**PROFIT & LOSS IMPACT**",
        f"- **Net Income:** ${net_income:,.2f}",
        "\n**SUMMARY TOTALS**",
        f"- **Total Assets:** ${total_assets:,.2f}",
        f"- **Total Liabilities:** ${total_liabilities:,.2f}",
        f"- **Total Equity (After Net Income & Capital):** ${total_equity:,.2f}",
        f"- **Liabilities + Equity:** ${total_liability_equity:,.2f}",
        "\n**ACCOUNTING EQUATION CHECK**",
        f"Assets = Liabilities + Equity → ${total_assets:,.2f} = ${total_liability_equity:,.2f} "
        f"(**{'Balanced' if abs(total_assets - total_liability_equity) < 0.01 else 'Imbalanced!'}**)"
    ]

    return "\n".join(summary)
