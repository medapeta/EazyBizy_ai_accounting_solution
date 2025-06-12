from flask import Flask, flash, redirect, render_template, request, url_for, make_response
from flask_session import Session as Flasksession
from sqlalchemy import create_engine, func, extract
from sqlalchemy.orm import sessionmaker,joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
from helper import * #query_transaction_data ,get_profit_loss_data,get_balance_sheet_data , get_ledger_data,show_income_expense_chart, show_cash_chart,ask_deepseek
from weasyprint import HTML
from flask_mail import Mail, Message
from extension import db # to avoid circular import problem
from collections import defaultdict, OrderedDict

load_dotenv()  # Load from .env file



load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

# ===== Database Configuration =====
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)

db.init_app(app)

from models import * 

with app.app_context():
    db.create_all()
    print("✅ Tables created")

# Session config
app.config["SESSION_TYPE"] = "sqlalchemy"
app.config["SESSION_SQLALCHEMY"] = db
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
Flasksession(app)

# ===== Mail Configuration =====
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
mail = Mail(app)


@app.route("/")
def index():
    return render_template("index.html",current_year=datetime.now().year)


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == 'POST':
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("User name is Empty","error")
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
           flash("Password is Empty", "error")
           return redirect("/login")
        
        login_username = request.form.get("username")
        login_password = request.form.get("password")

        #check database if such user exists 
        user_in_db = db.session.query(users_db).filter_by(username=login_username).first()

        #if exists create a session["username"] and continue
        if user_in_db and check_password_hash(user_in_db.password_hash, login_password):
            # Forget any user_id
            session.clear()
            session["user_id"] = user_in_db.id
            session["bussiness_name"] = user_in_db.bussiness_name
            flash(f'Wellcome back {user_in_db.username} you are logged in!', "success")
            return redirect("/dashboard")
        
        #if don't exist redirect to login
        else:
            flash("Invalid username or password", "error")
            return redirect(url_for('login'))
        
    return render_template("login.html",current_year=datetime.now().year)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        bussiness_name = request.form.get("bussiness_name")
        password = str(request.form.get("password"))
        confirm_password = request.form.get("confirm_password")

        # Validate inputs
        if not username:
            flash("Username is required", "error")
            return redirect("/register")
        if not email:
            flash("Email is required", "error")
            return redirect("/register")
        if not bussiness_name:
            flash("Business name is required", "error")
            return redirect("/register")
        if not password:
            flash("Password is required", "error")
            return redirect("/register")
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect("/register")

        # checking the validation of password length
        if len(password) < 6:
            flash("Password must be greater than 6 characters", "error")
            return redirect("/register")
        # Check if username or business name or email already exists
        existing_user = db.session.query(users_db).filter(
            (users_db.username == username) | 
            (users_db.bussiness_name == bussiness_name) | 
            (users_db.email == email)).first()
        print("existing_user:", existing_user)
        if existing_user:
            flash("Username, email, or business name already taken", "error")
            return redirect("/register")

        # Hash password and create new user
        hashed_pw = generate_password_hash(password)

        new_user = users_db(
            username=username,
            email=email,
            bussiness_name=bussiness_name,
            password_hash=hashed_pw
        )
        db.session.add(new_user)
        db.session.commit()
       
        # Log user in (create session)
        session["user_id"] = new_user.id
        session["bussiness_name"] = new_user.bussiness_name
        plant_capital = chart_of_accounts_db(
                user_id= session["user_id"],
                name = session['bussiness_name'] + "'s capital",
                type='equity',
                normal_side = 'credit',
                code=305,
                opening_balance=0
        )
        db.session.add(plant_capital)
        db.session.commit()
        flash(f"Welcome {username}, your account has been created!", "success")
        return redirect("/dashboard")

    # GET request
    return render_template("register.html",current_year=datetime.now().year)


@app.route("/about")
def about():
    return render_template("about_eazybizy.html")

@app.route("/dashboard")
@login_required
def dashboard():
    #business data 
    user = db.session.query(users_db).filter_by(id=session["user_id"]).first()
    bussiness_name = user.bussiness_name
    username = user.username


    *_,total_ie = get_profit_loss_data()
    income = total_ie["incomes"] 
    expense = total_ie["expenses"] 
    net = total_ie["net"] 


    asset,liability,equity,total_bs = get_balance_sheet_data()

    #net_worth/current capital
    net_worth = total_bs["equity"] 

    recent_transactions = (
        db.session.query(
            transactions_db.date,
            transactions_db.description,
            func.sum(transaction_detail_db.amount).label('amount')
        )
        .join(transaction_detail_db)
        .group_by(transactions_db.id)
        .order_by(transactions_db.date.desc())
        .limit(5)
        .all()
    )

    # Get current date
    today = datetime.today()
    # Format it: "Monday, 16 January 2026"
    formatted_date = today.strftime("%A, %d %B %Y")

    # Get current year and month
    now = datetime.utcnow()
    year = now.year
    month = now.month

    #chart data 
    i,e = show_income_expense_chart()
    cash_balances, cash_dates = show_cash_chart()
    cash_on_hand = cash_balances[-1]
    return render_template("main/dashboard.html",username=username,bussiness_name=bussiness_name,formatted_date=formatted_date, income=income, expense=expense, net=net, 
                           cash_on_hand=cash_on_hand, net_worth=net_worth,
                           recent_transactions=recent_transactions,i=i,e=e,cash_balances=cash_balances, cash_dates=cash_dates)

    
@app.route('/transactions/transactions_list')
@login_required
def transactions_list():
    # Get all transactions for the current user
    transactions = (
        db.session.query(transactions_db)
        .filter_by(user_id=session["user_id"])
        .order_by(transactions_db.date.desc())
        .all()
    )

    # For each transaction, fetch related details with account and category names
    transactions_data = []
    for txn in transactions:
        details = (
            db.session.query(
                transaction_detail_db,
                chart_of_accounts_db.name.label("account_name"),
                categories_db.name.label("category_name")
            )
            .join(chart_of_accounts_db, transaction_detail_db.account_id == chart_of_accounts_db.id)
            .outerjoin(categories_db, transaction_detail_db.category_id == categories_db.id)
            .filter(transaction_detail_db.transaction_id == txn.id)
            .all()
        )

        txn_details = []
        for detail, account_name, category_name in details:
            txn_details.append({
                'account_name': account_name,
                'category_name': category_name,
                'amount': float(detail.amount),
                'is_debit': detail.is_debit,
                
            })

        transactions_data.append({
            'id': txn.id,
            'date': txn.date,
            'description': txn.description,
            'reference_number': txn.reference_number,
            'details': txn_details
        })

    return render_template("/main/transactions/transactions_list.html", transactions=transactions_data)

@app.route('/transactions/delete_all', methods=["GET", "POST"])
@login_required
def transactions_reset():
    user_id = session.get("user_id")
    transactions = db.session.query(transactions_db).filter_by(user_id=user_id).all()
    for trx in transactions:
        if not transactions:
            flash("No transaction found", "danger")
            return redirect(url_for('transactions_list'))
        
        try:
            # Delete details first
            db.session.query(transaction_detail_db).filter_by(transaction_id=trx.id).delete()

            # Delete main transaction
            db.session.delete(trx)
            db.session.commit()
            flash("Transaction deleted successfully.", "success")
        except SQLAlchemyError:
            db.session.rollback()
            flash("An error occurred while deleting the transaction.", "danger")
    
    return redirect(url_for('transactions_list'))

@app.route('/transactions/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    user_id = session.get("user_id")

    transaction = db.session.query(transactions_db).filter_by(id=transaction_id, user_id=user_id).first()
    if not transaction:
        flash("Transaction not found or unauthorized.", "danger")
        return redirect(url_for('transactions_list'))

    try:
        # Delete details first
        db.session.query(transaction_detail_db).filter_by(transaction_id=transaction.id).delete()

        # Delete main transaction
        db.session.delete(transaction)
        db.session.commit()
        flash("Transaction deleted successfully.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("An error occurred while deleting the transaction.", "danger")

    return redirect(url_for('transactions_list'))

@app.route('/transactions/add_transactions', methods=["POST","GET"])
@login_required
def add_transactions():
        #ai response from other func
        ai_response = request.args.get("ai_response")

        accountz = db.session.query(chart_of_accounts_db).filter_by(user_id = session["user_id"]).all()
        


        if request.method == "POST":
            datestr = request.form.get("date")
            if not datestr:
                flash("Please select a date.", "danger")
                return redirect(request.url)

            dates = datetime.strptime(datestr, "%Y-%m-%d")

            descriptions = request.form.get("description")
            reference_number = request.form.get("reference_number")
            #transaction lines data 
            account_ids = request.form.getlist("account_id[]")
            category_ids = request.form.getlist("category_id[]")
            amounts = request.form.getlist("amount[]")

            d_c = request.form.getlist("d_c[]")

            #redirect to add_transactions page if debit!=credit balance
            total_debits = []
            total_credits = []

            for i in range(len(account_ids)):
                if d_c[i] == "debit":
                    total_debits.append(float(amounts[i]))
                elif d_c[i] == "credit":
                    total_credits.append(float(amounts[i]))

            if round(sum(total_credits), 2) != round(sum(total_debits), 2):
                flash("Debits and Credits are not equal. Please check your entries.", "info")
                return redirect(url_for('add_transactions'))

            

            #creating a transaction data in transactions_db
            new_transaction = transactions_db(
                user_id = session["user_id"],
                date = dates,
                description = descriptions,
                reference_number = reference_number
            )
            db.session.add(new_transaction)
            db.session.commit()

            # Get the committed transaction with its ID
            transaction_id_ = new_transaction.id


            # Process only filled lines
            for i in range(len(account_ids)):
                if account_ids[i] and amounts[i]:  # Ensure required fields
                    # Convert and use data
                    acct_id = int(account_ids[i])
                    amt = float(amounts[i])
                    
                    check_account_side = db.session.query(chart_of_accounts_db).filter_by(id = acct_id).first()
                    # Create transaction line here
                    new_transaction_line = transaction_detail_db(
                        transaction_id = transaction_id_,
                        account_id = acct_id,
                        amount = amt,
                        #tax_rate_id = tax_rate_ids[i] if tax_rate_ids[i] else None,
                        is_debit = True if d_c[i] == ("debit") else False,
                        
                    )

                    db.session.add(new_transaction_line)
            db.session.commit()
            flash("Transaction added successfully!", "success")

        return render_template("/main/transactions/add_transactions.html",ai_response=ai_response ,accounts=accountz)#, categories=catetoriztax_rates=taxz

#deepseek ai help using their free api
@app.route("/transactions/add_transactions/ai_help", methods=["POST","GET"])
@login_required
def ai_transaction_help():
    user_input = request.form.get("transactionInput", "")
    system_prompt = """
    You are a financial assistant. For any transaction description provided, identify all relevant accounts involved. 
    For each, determine the category (Revenue, Expense, Asset, Liability, or Equity) and whether it should be Debited or Credited.
    Respond using this exact format:
    [Account name]: [Category] → [Debit/Credit] → [amount] → [reson]
    Return only the accounts in this format, with each account on a **new line** using `\n`.
    remove any spaces before the response this is important.
    If there are multiple accounts, list each on a separate line. Do not add any explanation or extra text.
    """
    ai_response = ask_deepseek(user_input,system_prompt)

    return render_template("/main/transactions/add_transactions.html", ai_response=ai_response)

# Reports
@app.route("/reports/ledger_view")
@login_required
def report_ledger_view():

    accountz,_ = get_ledger_data()

    return render_template("main/reports/ledger_view.html",accountz=accountz)



@app.route("/reports/trial_balance")
@login_required
def report_trial_balance():
    # Custom labels and ordering
    type_order = ['asset', 'liability', 'equity', 'revenue', 'expense']
    type_labels = {
        'asset': 'A - Assets',
        'liability': 'L - Liabilities',
        'equity': 'EQ - Equity',
        'revenue': 'R - Revenue',
        'expense': 'EX - Expenses',
    }

    # Get all accounts for the user
    all_accounts = db.session.query(chart_of_accounts_db)\
        .filter_by(user_id=session["user_id"])\
        .options(joinedload(chart_of_accounts_db.transaction_lines))\
        .order_by(chart_of_accounts_db.type, chart_of_accounts_db.name)\
        .all()

    grouped_accounts_temp = defaultdict(list)
    total_dc = {"debits": 0, "credits": 0}

    # Loop through each account
    for account in all_accounts:
        balance = account.opening_balance or 0

        # Add up transaction effects
        for line in account.transaction_lines:
            if line.transaction.user_id != session["user_id"]:
                continue  # Skip unrelated
            if account.normal_side == 'debit':
                balance += line.amount if line.is_debit else -line.amount
            else:
                balance += -line.amount if line.is_debit else line.amount

        grouped_accounts_temp[account.type.lower()].append({
            "account_x": account,
            "account_total": balance,
            "lines": account.transaction_lines
        })

        # Update totals
        if account.normal_side == "debit":
            total_dc["debits"] += balance
        else:
            total_dc["credits"] += balance

    # Sort into custom order
    grouped_accounts = OrderedDict()
    for t in type_order:
        if t in grouped_accounts_temp:
            grouped_accounts[type_labels[t]] = grouped_accounts_temp[t]

    total_dc["balanced"] = abs(total_dc["debits"] - total_dc["credits"]) < 0.01

    return render_template(
        "main/reports/trial_balance.html",
        grouped_accounts=grouped_accounts,
        total_dc=total_dc,
        current_date=datetime.now()
    )



@app.route("/reports/profit_loss")
@login_required
def report_profit_loss():

    #uses the helper functions
    income,expense,total_ie = get_profit_loss_data()

    return render_template("main/reports/profit_loss.html",income=income, expense=expense, total_ie=total_ie)

@app.route("/reports/pdf/profit_loss")
@login_required
def print_profit_loss():

    #uses the helper functions
    income,expense,total_ie = get_profit_loss_data()

    rendered_html =render_template("main/reports/pdf/profit_loss.html", income=income,expense=expense,total_ie=total_ie)
    pdf = HTML(string=rendered_html).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=profit_loss.pdf'
    return response

#deepseek ai analysis using their free api
@app.route("/reports/profit_loss/ai_analysis", methods=["POST","GET"])
@login_required
def ai_profit_loss_analysis():
    user_input = format_pl_data()

    system_prompt =  """You are a financial analyst.

                        Analyze the following profit and loss summary and return a brief, helpful financial report formatted in clean HTML for a web dashboard. Use:

                        - Headings (<h5>, <strong>)
                        - Bullet points (<ul>, <li>)
                        - Paragraphs (<p>)
                        - Bold text (<strong>) for key figures or terms

                        Focus your analysis on:
                        - Profitability (e.g. net profit margin)
                        - Expense breakdown
                        - Revenue sources
                        - Red flags or anomalies
                        - Suggestions for the business owner

                        Make the content easily scannable and readable in a Bootstrap-styled card. Avoid long text blocks. Limit to 3–5 concise insights.
                        """

    ai_response = ask_deepseek(user_input,system_prompt)

    return jsonify({"ai_response": ai_response})


@app.route("/reports/balance_sheet")
@login_required
def report_balance_sheet():
    grouped_lines = query_transaction_data()

    # Calculate Net Income/Loss
    *_, total_ie = get_profit_loss_data()
    net_income = total_ie["net"]

    # Get all accounts for the current user
    all_accounts = db.session.query(chart_of_accounts_db)\
        .filter_by(user_id=session["user_id"])\
        .options(joinedload(chart_of_accounts_db.transaction_lines))\
        .order_by(chart_of_accounts_db.type, chart_of_accounts_db.name)\
        .all()
    # Prepare dict of transactions for quick lookup by account id
    transactions_by_account = {account.id: txns for account, txns in grouped_lines.items()}

    assets = []
    liabilities = []
    equity = []

    total_assets = 0
    total_liabilities = 0
    total_equity = 0

    for account in all_accounts:
        balance = account.opening_balance

        # Add transaction amounts if exist
        txns = transactions_by_account.get(account.id, [])
        for txn in txns:
            if account.normal_side == 'debit':
                balance += txn.amount if txn.is_debit else -txn.amount
            else:
                balance += -txn.amount if txn.is_debit else txn.amount

        entry = {
            "account_x": account,
            "account_total": balance
        }

        atype = account.type.lower()
        if atype == "asset":
            assets.append(entry)
            total_assets += balance
        elif atype == "liability":
            liabilities.append(entry)
            total_liabilities += balance
        elif atype == "equity":
            equity.append(entry)
            total_equity += balance

    # Add net income/loss
    equity.append({
        "account_x": {
            "name": "Current Period Earnings" if net_income >= 0 else "Current Period Loss",
            "type": "Equity",
            "normal_side": "credit" if net_income >= 0 else "debit"
        },
        "account_total": abs(net_income)
    })
    total_equity += net_income

    total_liability_equity = total_liabilities + total_equity

    return render_template(
        "main/reports/balance_sheet.html",
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        total_liability_equity=total_liability_equity,
        is_balanced=abs(total_assets - total_liability_equity) < 0.01
    )

#deepseek ai analysis using their free api
@app.route("/reports/balance_sheet/ai_analysis", methods=["POST","GET"])
@login_required
def ai_balance_sheet_analysis():
    user_input = format_balance_sheet_data_for_ai()

    system_prompt = """
                    You are a financial analyst.

                    Analyze the following balance sheet summary and provide a short, insightful report formatted in clean HTML suitable for a web dashboard. Use:

                    - Headings (<h5>, <strong>)
                    - Bullet points (<ul>, <li>)
                    - Paragraphs (<p>)
                    - Bold text (<strong>) for key figures or categories

                    Include in your analysis:
                    - Overview of Assets, Liabilities, and Equity
                    - Observations about liquidity, solvency, or unusual balances
                    - Highlight any red flags (e.g., excessive liabilities or low equity)
                    - Recommendations or next steps

                    Make the content brief (about 3–5 points), well-structured, and easy to scan. Avoid long paragraphs.

                    """


    ai_response = ask_deepseek(user_input,system_prompt)

    return jsonify({"ai_response": ai_response})


@app.route("/reports/pdf/balance_sheet")
@login_required
def print_balance_sheet():
    grouped_lines = query_transaction_data()
    all_accounts = db.session.query(chart_of_accounts_db)\
        .filter_by(user_id=session["user_id"])\
        .options(joinedload(chart_of_accounts_db.transaction_lines))\
        .order_by(chart_of_accounts_db.type, chart_of_accounts_db.name)\
        .all()
    transactions_by_account = {account.id: txns for account, txns in grouped_lines.items()}

    assets, liabilities, equity = [], [], []
    total_assets = total_liabilities = total_equity = 0

    for account in all_accounts:
        balance = account.opening_balance
        txns = transactions_by_account.get(account.id, [])
        for txn in txns:
            if account.normal_side == 'debit':
                balance += txn.amount if txn.is_debit else -txn.amount
            else:
                balance += -txn.amount if txn.is_debit else txn.amount

        entry = {"account_x": account, "account_total": balance}
        atype = account.type.lower()

        if atype == 'asset':
            assets.append(entry)
            total_assets += balance
        elif atype == 'liability':
            liabilities.append(entry)
            total_liabilities += balance
        elif atype == 'equity':
            equity.append(entry)
            total_equity += balance

    # Net Income
    *_, total_ie = get_profit_loss_data()
    net_income = total_ie["net"]
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

    # Owner's Capital
    capital_account_name = f"{session.get('bussiness_name', 'Business')} Capital"
    capital_balance = 0
    for account in all_accounts:
        if account.type.lower() == 'equity' and capital_account_name in account.name:
            capital_balance = account.opening_balance
            txns = transactions_by_account.get(account.id, [])
            for txn in txns:
                if account.normal_side == 'debit':
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

    total_bs = {
        "assets": total_assets,
        "liabilities": total_liabilities,
        "equity": total_equity,
    }

    # 🔽 Render HTML and generate PDF
    rendered_html = render_template(
        "main/reports/pdf/balance_sheet.html",
        net=net_income,
        total_bs=total_bs,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        total_equity=total_equity,
        total_liability_equity=total_liability_equity
    )

    pdf = HTML(string=rendered_html).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=balance_sheet.pdf'
    return response



# Settings

@app.route("/settings/accounts", methods=['GET', 'POST'])
@login_required
def settings_accounts():
    if request.method == 'POST':
        try:
            name = request.form['name']
            type_ = request.form['type']
            code = request.form.get('code')
            opening_balance_raw = request.form.get('opening_balance')
            opening_balance = float(opening_balance_raw) if opening_balance_raw else 0.00

            if type_ in ("Asset", "Expense"):
                    normal_side_ = "debit"
            elif type_ in ("Liability", "Equity", "Revenue"):
                    normal_side_ = "credit"


            new_account = chart_of_accounts_db(
                user_id= session["user_id"],
                name=name,
                type=type_,
                normal_side = normal_side_,
                code=code,
                opening_balance=opening_balance
            )

            db.session.add(new_account)
            db.session.commit()
            flash('Account added successfully!', 'success')
            return redirect("/settings/accounts")

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding account: {str(e)}', 'danger')

    accounts = db.session.query(chart_of_accounts_db).filter_by(user_id=session["user_id"]).order_by(chart_of_accounts_db.created_at.asc()).all()

    return render_template("main/settings/accounts.html", accounts=accounts)

@app.route("/edit_account/<int:account_id>", methods=["POST"])
@login_required
def edit_account(account_id):
    account = db.session.query(chart_of_accounts_db).get(account_id)
    if account:
        account.name = request.form["name"]
        account.type = request.form["type"]
        account.code = request.form["code"]
        account.opening_balance = request.form["opening_balance"]
        account.is_system_account = "is_system_account" in request.form
        db.session.commit()
        flash("Account updated successfully!", "success")
    return redirect(url_for("settings_accounts")) 

@app.route("/delete_account/<int:account_id>", methods=["POST"])
@login_required
def delete_account(account_id):
    account = db.session.query(chart_of_accounts_db).get(account_id)
    if account:
        db.session.delete(account)
        db.session.commit()
        flash("Account deleted successfully!", "success")
    return redirect(url_for("settings_accounts")) 

@app.route("/settings/categories", methods=['GET', 'POST'])
@login_required
def settings_categories():
    if request.method == 'POST':
        try:
            name = request.form['name']
            type_ = request.form['type']
            parent_id = request.form.get('parent') or None
            

            # Optional: Convert to int if needed
            parent_category_id = parent_id if parent_id else None
           

            # Now you can use parent_category_id and tax_rate_id when creating the new category
            new_category = categories_db(
                user_id= session["user_id"],
                name=name,
                type=type_,
                parent_category_id=parent_category_id,
                 
            )

            db.session.add(new_category)
            db.session.commit()
            flash('Category added successfully!', 'success')
            return redirect("/settings/categories")

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding account: {str(e)}', 'danger')

    categories_ = db.session.query(categories_db).filter_by(user_id=session["user_id"]).all()
    return render_template("main/settings/categories.html",categories=categories_)#,tax_rates_list=tax_rates_list

@app.route("/edit_category/<int:category_id>", methods=["POST"])
@login_required
def edit_category(category_id):
    category = db.session.query(categories_db).get(category_id)
    if category:
        category.name = request.form["name"]
        category.type = request.form["type"]
        parent_id = request.form.get("parent_category_id")
        category.parent_category_id = int(parent_id) if parent_id else None

        db.session.commit()
    return redirect(url_for("settings_categories"))

@app.route("/delete_category/<int:category_id>", methods=["POST"])
@login_required
def delete_category(category_id):
    category = db.session.query(categories_db).get(category_id)
    if category:
        db.session.delete(category)
        db.session.commit()
        flash("Category deleted successfully!", "success")
    return redirect(url_for("settings_categories")) 

@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    user = db.session.query(users_db).filter_by(id=session["user_id"]).first()

    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get("username", "").strip()
            bussiness_name = request.form.get("bussiness_name", "").strip()
            currency = request.form.get("currency", "").strip()
            # After getting form input
            fiscal_year_str = request.form.get("fiscal_year_start", "").strip()

            # Parse only once
            fiscal_year = datetime.strptime(fiscal_year_str, "%Y-%m-%d").date() if fiscal_year_str else None

            # Optional: validate here, but you already parsed it safely
            user.fiscal_year_start = fiscal_year

            
            # Validate all fields
            errors = []
            
            if not username:
                errors.append("Username is required")
            elif len(username) > 50:
                errors.append("Username must be less than 50 characters")
                
            if not bussiness_name:
                errors.append("Business name is required")
            elif len(bussiness_name) > 100:
                errors.append("Business name must be less than 100 characters")
                
            if not currency:
                errors.append("Currency is required")
                
            if not fiscal_year:
                errors.append("Fiscal year start date is required")
            
            if errors:
                for error in errors:
                    flash(error, "error")
                return redirect(url_for('settings_profile'))  # Changed to current endpoint
            
            # Update user if validation passes
            user.username = username
            user.bussiness_name = bussiness_name
            user.currency = currency
            user.fiscal_year_start = fiscal_year  # Make sure this matches your model
            
            db.session.commit()
            flash("Profile updated successfully!", "success")
            return redirect(url_for('settings_profile'))  # PRG pattern
            
        except IntegrityError as e:
            db.session.rollback()
            if "NOT NULL constraint" in str(e):
                flash("Required fields cannot be empty", "error")
            else:
                flash("A database error occurred", "error")
            return redirect(url_for('settings_profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"An unexpected error occurred: {str(e)}", "error")
            return redirect(url_for('settings_profile'))


    # GET request or form display
    return render_template("main/settings/profile.html", 
                         user=user,
                         current_year=datetime.now().year)  # Added helpful template variable


@app.route('/settings/profile/delete', methods=['GET', 'POST'])
@login_required
def delete_profile():
    user_id = session["user_id"]

    # Load user along with their accounts, categories, and transactions
    user = db.session.query(users_db).options(
        joinedload(users_db.accounts),
        joinedload(users_db.categories),
        joinedload(users_db.transactions)
    ).get(user_id)

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('index'))

    db.session.delete(user)
    db.session.commit()
    session.clear()
    flash("Profile deleted successfully", "success")
    return redirect(url_for('index'))


@app.route('/settings/report_problem', methods=['GET', 'POST'])
def report_problem():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        
        msg = Message(
            subject=f"[Problem Report] {subject}",
            recipients=['petrosmedhanie59@gmail.com'],  
            body=f"""
                        A user has reported a problem:

                        Name: {name}
                        Email: {email}
                        Subject: {subject}

                        Message:
                        {message}
                        """
                                )

        try:
            mail.send(msg)
            flash("Your report has been sent successfully!", "success")
        except Exception as e:
            print(e)
            flash("There was an error sending your report. Please try again later.", "danger")

        return redirect('/settings/report_problem')
    return render_template('main/settings/problem_report.html')
@app.route('/logout')
def logout():
    session.clear()
    db.session.close()
    flash("You have logged out", "success")
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=False)
