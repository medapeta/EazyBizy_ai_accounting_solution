from flask import Flask, flash, redirect, render_template, request, url_for, make_response
from flask_session import Session as Flasksession
from sqlalchemy import create_engine, func, extract, inspect
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
from helper import * #query_transaction_data ,get_profit_loss_data,get_balance_sheet_data , get_ledger_data,show_income_expense_chart, show_cash_chart,ask_deepseek
from weasyprint import HTML
from flask_mail import Mail, Message
from extension import db # to avoid circular import problem


load_dotenv()  # Load from .env file

app = Flask(__name__)


# ===== Core Configurations =====
app.secret_key = os.getenv("SECRET_KEY")

# ===== Database Configuration =====
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")#, "sqlite:///ai-bookeeping.db"
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)

# Initialize db
db.init_app(app)


# Auto-create tables if not already there
def initialize_database():
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.get_table_names():
            db.create_all()
            print("✅ Database initialized.")

initialize_database()

from models import *

app.config["SESSION_TYPE"] = "sqlalchemy"
app.config["SESSION_SQLALCHEMY"] = db  
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
Flasksession(app)  # Create Session object

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
    #Log user in
    # Forget any user_id
    session.clear()

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
            session["user_id"] = user_in_db.id
            flash(f'Wellcome back {user_in_db.username} you are logged in!', "success")
            return redirect("/dashboard")
        
        #if don't exist redirect to login
        else:
            flash("Invalid username or password", "error")
            return redirect("/login")
        
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
        print("New user ID after commit:", new_user.id)
        # Log user in (create session)
        session["user_id"] = new_user.id
        flash(f"Welcome {username}, your account has been created!", "success")
        return redirect("/dashboard")

    # GET request
    return render_template("register.html",current_year=datetime.now().year)

@app.route("/help")
def help():
    return render_template("main/help.html")

@app.route("/about")
def about():
    return render_template("about_eazybizy.html")

@app.route("/dashboard")
@login_required
def dashboard():
    #business data 
    user = db.session.query(users_db).filter_by(id=session["user_id"]).first()
    business_name = user.bussiness_name
    username = user.username


    *_,total_ie = get_profit_loss_data()
    income = total_ie["incomes"] 
    expense = total_ie["expenses"] 
    net = total_ie["net"] 


    asset,liability,equity,total_bs = get_balance_sheet_data()
    cash_on_hand = 0
    #cash_on_hand
    for acc in asset:
        if acc["account_x"].name == 'cash':
            cash_on_hand = acc["account_total"] if acc["account_total"] is not None else 0
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

    return render_template("main/dashboard.html",username=username,business_name=business_name,formatted_date=formatted_date, income=income, expense=expense, net=net, 
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

        accountz = db.session.query(chart_of_accounts_db).all()
        catetoriz = db.session.query(categories_db).all()


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

        return render_template("/main/transactions/add_transactions.html",ai_response=ai_response ,accounts=accountz, categories=catetoriz)#tax_rates=taxz

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

    accountz = []

    group_accounts = query_transaction_data()

    for acct, trxs in group_accounts.items():
        accounts = {}
        accounts["account_x"] = acct # we need the name, type , normal_side and code of the account

        #now let's grap the account totals
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
        accountz.append(accounts)


    # taking total off all debits and total credits
    total_dc = {}
    total_debits = []
    total_credits = []
    for acc in accountz:
        if acc["account_x"].normal_side == "debit":
            total_debits.append(acc["account_total"])
        else:
            total_credits.append(acc["account_total"])
    total_dc["debits"] = sum(total_debits)
    total_dc["credits"] = sum(total_credits)
    return render_template("main/reports/trial_balance.html",accountz=accountz,total_dc=total_dc)

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
    asset,liability,equity,total_bs = get_balance_sheet_data()
    *_,total_ie = get_profit_loss_data()
    net = total_ie["incomes"] - total_ie["expenses"]
    total_equity = total_bs["equity"] + net
    total_liability_equity = total_equity  + total_bs["liabilities"]
    return render_template("main/reports/balance_sheet.html", total_bs=total_bs,assets=asset,liabilities=liability,equity=equity,net=net,total_equity=total_equity,total_liability_equity=total_liability_equity)

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
    asset,liability,equity,total_bs = get_balance_sheet_data()
    *_,total_ie = get_profit_loss_data()
    net = total_ie["incomes"] - total_ie["expenses"]
    total_equity = total_bs["equity"] + net
    total_liability_equity = total_equity  + total_bs["liabilities"]
    rendered_html =render_template("main/reports/pdf/balance_sheet.html", total_bs=total_bs,assets=asset,liabilities=liability,equity=equity,net=net,total_equity=total_equity,total_liability_equity=total_liability_equity)

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
            #tax_rate_id = request.form.get('tax_rate_id') or None  # Use exact name from form input

            # Optional: Convert to int if needed
            parent_category_id = parent_id if parent_id else None
           # tax_rate_id = tax_rate_id if tax_rate_id else None

            # Now you can use parent_category_id and tax_rate_id when creating the new category
            new_category = categories_db(
                user_id= session["user_id"],
                name=name,
                type=type_,
                parent_category_id=parent_category_id,
                #tax_rate_id=tax_rate_id   
            )

            db.session.add(new_category)
            db.session.commit()
            flash('Category added successfully!', 'success')
            return redirect("/settings/categories")

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding account: {str(e)}', 'danger')

    categories_ = db.session.query(categories_db).filter_by(user_id=session["user_id"]).all()
    #tax_rates_list = db.session.query(tax_rates_db).filter_by(user_id=session["user_id"]).all()
    return render_template("main/settings/categories.html",categories=categories_)#,tax_rates_list=tax_rates_list

@app.route("/edit_category/<int:category_id>", methods=["POST"])
@login_required
def edit_category(category_id):
    category = db.session.query(categories_db).get(category_id)
    if category:
        category.name = request.form["name"]
        category.type = request.form["type"]
        parent_id = request.form.get("parent_category_id")
        #tax_rate_id = request.form.get("tax_rate_id")

        category.parent_category_id = int(parent_id) if parent_id else None
        #category.tax_rate_id = int(tax_rate_id) if tax_rate_id else None

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

    if request.method == 'POST' and user:
        user.username = request.form.get("username")
        user.business_name = request.form.get("business_name")
        user.currency = request.form.get("currency")
        user.fiscal_year = request.form.get("fiscal_year_start")
        db.session.commit()
        flash("Profile updated successfully!", "success")

    return render_template("main/settings/profile.html", user=user)

@app.route('/settings/profile/delete', methods=['GET', 'POST'])
@login_required
def delete_profile():
    user = db.session.query(users_db).get(session["user_id"])
    db.session.delete(user)
    db.session.commit()
    session.clear()
    flash("Profile deleted. successfuly", "success")
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
