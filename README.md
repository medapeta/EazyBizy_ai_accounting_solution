# EazyBizy v1.0 - AI-Powered Bookkeeping Solution

**Author:** Medhanie Petros (Ola cs50)
**Project for:** CS50's Final Project

## Video Demo

[Link to Video Demo](https://youtu.be/YOUR_VIDEO_LINK_HERE)

## table of contents
- [Introduction](#introduction)
- [Bigger Picture](#bigger-picture)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- 
## Introduction

For my CS50 final project, I built EazyBizy, a simple bookkeeping web app for freelancers and small business owners who find traditional accounting software intimidating.
The core feature is an AI assistant that helps you categorize transactions. You can just type what happened in plain English, like "bought office supplies with cash," and the AI will suggest the correct accounting entries. It also generates essential reports like a Profit & Loss statement that you can export to PDF.

## Bigger Picture
This github repository contains two important branches the localDeployment (you can see how to implement this on your machine later) and the renderDeployment which is deployed in render.com under the subdomain name (https://eazybizy.onrender.com). 

* ## Live Version (renderDeployment Branch) (https://eazybizy.onrender.com)
This Branch is deployed on render and it is the same to the local version execept that it uses render's Postgres Database and Flask-Sqlalchemy to handle it. The PostgreSQL was implemented because its a production-grade, server-based database that supports concurrent access, scalability, and better reliability in web environments—while SQLite is a lightweight, file-based database that's better suited for local development or single-user apps.

* ## Local Version (renderDeployment Branch)
This Branch can be cloned from github and run on your machine is uses raw Sqlalchemy and SQLite3 for local deployment because it’s lightweight, requires zero setup, and is perfect for quick development and testing on a local machine. It stores the entire database in a single file, making it easy to manage and share during development.

Other differences and similiarities between this branches is explained in detail on the topics below.


## Key Features

*   **Secure User Authentication:** Unique user accounts with hashed passwords to keep financial data private.
*   **Intuitive Dashboard:** At-a-glance view of key financial metrics like Cash on Hand, Income, Expenses, and Net Worth.
*   **Visual Charts:** Doughnut and Line charts to visualize income vs. expense breakdown and cash flow over time.
*   **AI-Assisted Transactions:** Users can input a plain-English description of a transaction and receive AI-powered suggestions for debit/credit entries.
*   **Double-Entry Bookkeeping:** Enforces the fundamental accounting principle that debits must equal credits for every transaction.
*   **Customizable Chart of Accounts:** Users can create, edit, and delete accounts to tailor the system to their specific business needs.
*   **Comprehensive Financial Reports:**
    *   General Ledger
    *   Trial Balance
    *   Profit & Loss Statement
    *   Balance Sheet
*   **AI Financial Analysis:** Users can request an AI-generated analysis of their P&L Statement and Balance Sheet for insights and recommendations.
*   **PDF Export:** Generate professional, printable PDF versions of the P&L Statement and Balance Sheet.
*   **Profile Management:** Users can update their business details and, if necessary, delete their entire profile and associated data.

## Technology Stack

EazyBizy is built with a robust and modern technology stack:

*   **Backend:** Python, Flask
*   **Database:** SQLAlchemy ORM (compatible with SQLite for development and PostgreSQL for production)
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
*   **AI Integration:** DeepSeek model via OpenRouter API
*   **PDF Generation:** WeasyPrint
*   **Emailing:** Flask-Mail (for problem reporting)
*   **Data Visualization:** Chart.js
*   **Environment Management:** `python-dotenv`

## Directory Structure

The project is organized following standard Flask application conventions to ensure maintainability and scalability.


```
├── EazyBizy_ai_bookeeping/
│   ├── app.py                  # Main Flask application file (differs between versions)
│   ├── extension.py            # (Live Version Only) Manages Flask extensions
│   ├── helper.py               # (differs slightly between versions)
│   ├── init_db.py              # (Local Version Only) Manual database creation script
│   ├── models.py               # (differs between versions) SQLAlchemy models
│   ├── project_snapshot.py     # Script to generate project overview
│   ├── requirements.txt        # Python package dependencies
│   ├── flask_session/          # (Local Version) Server-side session storage
│   ├── instance/
│   ├── static/
│   │   ├── css/
│   │   ├── images/
│   │   └── js/
│   └── templates/              # Jinja2 HTML templates (shared)
│       ├── main/               # Templates for the main application (post-login)
│       │   ├── reports/
│       │   │   ├── pdf/        # PDF-specific templates
│       │   ├── settings/
│       │   └── transactions/
│       ├── about_eazybizy.html
│       ├── index.html
│       ├── layout.html
│       ├── login.html
│       └── register.html
```


## File Breakdown and Version Differences

### `app.py` (The Application Core)
This is the heart of the application, responsible for initializing the Flask app, configuring extensions, and defining all the routes (URL endpoints).

*   **Initialization:** Sets up Flask, SQLAlchemy, Flask-Session, and Flask-Mail. It reads configuration from environment variables for security.
*   **Authentication Routes:**
    *   `@app.route("/login")`: Handles user login. It validates credentials against the database and uses `check_password_hash` for security. On success, it creates a user session.
    *   `@app.route("/register")`: Manages new user registration. It validates form input, checks for existing users, hashes the password using `generate_password_hash`, and automatically creates a default "Owner's Capital" account for the new user.
    *   `@app.route("/logout")`: Clears the user session and logs the user out.
*   **Core App Routes:**
    *   `@app.route("/dashboard")`: The main landing page after login. It fetches data by calling multiple functions from `helper.py` to calculate key metrics (income, expense, net worth) and chart data, then renders the main dashboard.
*   **Transaction Routes:**
    *   `@app.route("/transactions/add_transactions")`: A dual-purpose route. For `GET`, it displays the form to add a new transaction. For `POST`, it processes the submitted form, ensures that total debits equal total credits, and saves the new transaction and its details to the database.
    *   `@app.route("/transactions/transactions_list")`: Displays a journal of all past transactions in reverse chronological order.
    *   `@app.route("/transactions/delete/<transaction_id>")`: Handles the deletion of a specific transaction and its associated detail lines.
*   **Report Routes:**
    *   `/reports/profit_loss`, `/reports/balance_sheet`, etc.: Each route is responsible for gathering the necessary data (by calling helpers) and rendering the corresponding HTML report.
    *   `/reports/pdf/...`: These routes take the data from their HTML counterparts, render a simplified PDF-specific template, and use WeasyPrint to generate a PDF response that can be viewed or downloaded.
*   **AI Analysis Routes:**
    *   `/reports/.../ai_analysis`: These endpoints are called via JavaScript (AJAX). They format the relevant financial data into a string, send it to the `ask_deepseek` helper function with a specific system prompt, and return the AI's HTML-formatted response as JSON.
*   **Settings Routes:**
    *   `/settings/accounts`: Allows users to view, add, edit, and delete accounts in their Chart of Accounts.
    *   `/settings/profile`: Allows users to view and update their business profile information.
    *   `/settings/report_problem`: Provides a form that, on submission, uses Flask-Mail to send an email to the administrator with the user's feedback or bug report.

### `helper.py` (Business Logic and Helpers)
This file separates the complex business logic from the routing in `app.py`, promoting cleaner code and better organization.

*   `login_required(f)`: A decorator function that protects routes from being accessed by non-logged-in users. It checks for a `user_id` in the session and redirects to the login page if it's not found.
*   `query_transaction_data()`: A fundamental helper that queries the database to get all transaction lines for the current user, grouped by their parent account. This is the foundation for most financial calculations.
*   `get_profit_loss_data()`: Calculates all income and expense account totals to generate the data needed for the Profit & Loss statement. It returns categorized lists and a summary dictionary.
*   `get_balance_sheet_data()`: Similar to the P&L helper, this function calculates totals for all Asset, Liability, and Equity accounts to build the Balance Sheet.
*   `get_ledger_data()`: Prepares data for the General Ledger view. For each account, it calculates a running balance after every transaction.
*   `show_..._chart()`: These functions process financial data into a format suitable for Chart.js on the dashboard.
*   `ask_deepseek(user_message, system_prompt)`: The core AI function. It constructs a request to the OpenRouter API with the user's query and a carefully crafted system prompt that instructs the AI on the desired output format and persona.
*   `format_..._data_for_ai()`: These functions take the complex data structures for the P&L and Balance Sheet and format them into a clean, human-readable string to be used as a prompt for the AI analysis feature.

### `models.py` (Database Schemas)
This file defines the structure of the database.

*   `users_db`: Stores user information, including credentials and business details.
*   `chart_of_accounts_db`: Stores the list of all financial accounts for each user (e.g., Cash, Sales, Rent Expense).
*   `transactions_db`: The header table for each transaction, containing the date, description, and user ID.
*   `transaction_detail_db`: The line-item table for transactions. Each row represents a debit or credit to a specific account, linked back to a master transaction.
*   **Relationships:** The models are interconnected using `relationship` in local version and `db.relationship` in live version, which allows SQLAlchemy to manage the connections (e.g., a user has many accounts, a transaction has many details). Cascading deletes are set up so that when a user or transaction is deleted, all their associated data is also removed.

### `extension.py` (A Key Design Choice used in the live version)
This small but crucial file exists to solve the problem of circular imports in Flask applications.
1.  `app.py` needs to import the models from `models.py`.
2.  `models.py` needs the `db` object from Flask-SQLAlchemy to define its models.
If the `db` object is initialized in `app.py`, this creates a circular dependency (`app.py` -> `models.py` -> `app.py`). By initializing `db = SQLAlchemy()` in `extension.py`, both `app.py` and `models.py` can import `db` from this central, neutral location, breaking the circle. `app.py` then completes the initialization with `db.init_app(app)`.

### `init_db.py` (also Key Design Choice used in the local version)
Also small yet crucial file exists as a utility script used during local developments.
1. imports Base from the models `models.py` create_engine from sqlalchemy.
2. it create the sqlite3 database.
3. creates the tables from `models.py` using  `create_all` and also has a commented command `drop_all` it in case it is needed to reset the database and start from scratch uncommend it run init_db.py and comment it becase it will reset again if not.
If the `db` object is initialized in `app.py`, this creates a circular dependency (`app.py` -> `models.py` -> `app.py`). By initializing `db = SQLAlchemy()` in `extension.py`, both `app.py` and `models.py` can import `db` from this central, neutral location, breaking the circle. `app.py` then completes the initialization with `db.init_app(app)`.

### Templates (`templates/`)
The templates are structured for reusability and clarity.
*   `layout.html`: The base template for public-facing pages (Home, Login, Register). It includes the main header, footer, and a block for content.
*   `dash_layout.html`: The base template for the authenticated part of the application. It includes the collapsible sidebar navigation, the top navigation bar, and the main content area. This is a powerful feature that ensures a consistent user experience across the entire app.
*   The subdirectories (`reports/`, `settings/`, `transactions/`) logically group the templates, making the project easier to navigate.
*   PDF templates (`templates/main/reports/pdf/`): These are simplified, style-only versions of the reports, designed specifically for clean rendering by WeasyPrint.
*   
### Difference Between Versions
As we saw `app.py` is responsible for initializing the Flask app and defining all routes. Its setup differs significantly between versions.

*   **Local Version:**
    *   **DB Setup:** Manually creates a SQLAlchemy engine and session using `create_engine` and `sessionmaker`. All database queries are performed through this manually created `db_session`.
    *   **Session Management:** Uses `Flasksession(app)` with the default `filesystem` type, which stores session files locally. This is simple and requires no database setup.
*   **Live Version:**
    *   **DB Setup:** Initializes the database via the Flask-SQLAlchemy extension imported from `extension.py`. It uses `db.init_app(app)` and creates tables within the application context. All queries use the extension's managed session: `db.session`.
    *   **Session Management:** Configured to use `SESSION_TYPE = "sqlalchemy"`. This stores session data within the main application database, which is more robust and scalable for a deployed environment.

### `models.py` (Database Schemas)
This file defines the database structure. The definitions are slightly different to accommodate the two SQLAlchemy patterns.

*   **Local Version:**
    *   Imports `declarative_base` from `sqlalchemy.orm`.
    *   The base class is created via `Base = declarative_base()`. All models inherit from this `Base`.
    *   Columns and relationships are defined using core SQLAlchemy types like `Column`, `Integer`, `ForeignKey`, etc.
*   **Live Version:**
    *   Imports the `db` object from `extension.py`.
    *   All models inherit from `db.Model`, the base class provided by the Flask-SQLAlchemy extension.
    *   Columns and relationships use the extension's helpers, like `db.Column`, `db.Integer`, `db.ForeignKey`, etc.

### `extension.py` (Live Version Only)
This small but crucial file exists to solve the problem of circular imports in Flask applications. In a larger app, `app.py` needs to import models from `models.py`, but `models.py` needs the `db` object to define its classes. By initializing `db = SQLAlchemy()` in this separate file, both `app.py` and `models.py` can import it without creating a dependency loop. This is a standard best practice for scalable Flask applications.

### `init_db.py` (Local Version Only)
This is a simple utility script used during local development. It imports the `Base` and `engine` from the models and `app.py` respectively, and runs `Base.metadata.create_all(engine)`. This manually creates the SQLite database file and all the necessary tables, giving the developer explicit control over the database creation process.

### `helper.py` (Business Logic and Helpers)
This file separates the complex business logic from the routing. It is largely identical between versions, with one minor but important difference:
*   **Local Version:** Creates its own database session: `Session = sessionmaker(bind=engine); db_session = Session()`.
*   **Live Version:** Imports the globally managed `db` object from `extension.py` and uses `db.session` for all queries.

The functions themselves (`get_profit_loss_data`, `ask_deepseek`, etc.) perform the same logic in both versions.

### Templates (`templates/`)
All Jinja2 templates are identical across both branches. They are designed to work with the data context provided by the routes in `app.py`, regardless of how that data was fetched from the database. This demonstrates a clean separation of concerns between the backend logic and the frontend presentation.

### Key Architectural Differences

| Feature             | Development Version (`eazybizy_ai_...`)                          | Production Version (`main`)                                        |
| ------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Database Init**   | Manual script (`init_db.py`)                                     | Automatic via Flask-SQLAlchemy (`db.create_all()`)                 |
| **DB Connection**   | Hardcoded `create_engine` in `app.py`                            | Configured via `DATABASE_URL` in `.env` file                       |
| **SQLAlchemy Usage**| Core ORM (`declarative_base`, `sessionmaker`)                    | Flask-SQLAlchemy extension (`db.Model`, `db.session`)              |
| **Session Storage** | `SESSION_TYPE = "filesystem"`                                    | `SESSION_TYPE = "sqlalchemy"` (stores sessions in the database)    |
| **Project Structure**| Simpler, all-in-one approach in `app.py`                         | Uses `extension.py` to prevent circular imports                    |
## Design Decisions and Trade-offs

*   **Database Choice (SQLite vs. PostgreSQL):** The application was developed using SQLite because it's a file-based database that requires zero setup, making local development incredibly fast and simple. However, the code is written to be production-ready. The `app.py` file includes logic to correctly format a PostgreSQL connection string, meaning the app can be deployed to a platform like Render or Heroku with a simple change to the `DATABASE_URL` environment variable. This provides the best of both worlds: ease of development and robustness for production.

*   **ORM over Raw SQL:** I chose to use the SQLAlchemy ORM instead of writing raw SQL queries. While raw SQL can sometimes be more performant for very complex queries, the ORM provides massive benefits for a project of this scale:
    *   **Developer Productivity:** It's faster to write `db.session.query(...)` than to manually construct SQL strings.
    *   **Security:** It automatically handles parameterization, which is the primary defense against SQL injection attacks.
    *   **Maintainability:** The Python-based query syntax is often more readable and easier to modify than complex SQL.
    *   **Database Agnosticism:** The same ORM code works for both SQLite and PostgreSQL.

*   **Server-Side Sessions:** Instead of using Flask's default client-side (cookie-based) sessions, I implemented `flask-session` with a filesystem backend. This is a security-conscious choice. Storing session data on the server prevents users from tampering with the session cookie content. For a production environment, this could easily be switched to a database or Redis backend for better scalability.

*   **Branching Strategy:** The project is maintained on GitHub with two primary branches:
    *   `main`: This branch represents the stable, deployed version of the application.
    *   `eazybizy_ai_accouting_solution`: This is the active development branch where new features are built and bugs are fixed before being merged into `main`. This practice ensures that the live version of the app remains stable while development continues.

## Future Improvements

*   **Tax Integration:** Add functionality to associate tax rates with transaction lines and generate tax summary reports.
*   **Bank Integration:** Use an API like Plaid to allow users to securely connect their bank accounts and automatically import transactions.
*   **Multi-User Collaboration:** Allow a business owner to invite their accountant or other team members to view or manage the books with different permission levels.
*   **Budgeting Module:** Enable users to set budgets for different expense categories and track their spending against those budgets.

The decision to maintain two distinct architectural patterns was deliberate and driven by the different goals of local development and production deployment.

### 1. The Local Development Environment (`eazybizy_ai_accouting_solution` branch)
The primary goal for this version was **simplicity and speed of iteration**.

*   **Why `init_db.py` and manual SQLAlchemy Core?**
    This approach provides direct, explicit control. For a developer learning the stack, it's beneficial to see the "raw" SQLAlchemy mechanics of creating an engine, a session, and running queries. There is less "magic" compared to the Flask-SQLAlchemy extension.
*   **Why SQLite?**
    SQLite is a serverless, file-based database. It requires zero setup, making it incredibly fast to get a development environment up and running. There's no need to install and configure a database server like PostgreSQL.
*   **Why Filesystem Sessions?**
    Similar to SQLite, filesystem sessions work out of the box with minimal configuration. They are perfectly adequate for a single developer working locally.

### 2. The Production-Ready Environment (`main` branch)
The goal for this version was **scalability, maintainability, and security**—all essential for a live application.

*   **Why `extension.py` and Flask-SQLAlchemy?**
    This pattern is the standard for building robust Flask applications. It solves the circular import problem elegantly and integrates the database session with the Flask application lifecycle (app context). This makes the code cleaner, more idiomatic, and easier for other Flask developers to understand.
*   **Why Environment Variables (`.env`) for Configuration?**
    This is a critical security practice. Hardcoding credentials (like database URLs or API keys) is dangerous. By loading these from an environment file (which is not committed to version control), the application can be deployed to any environment (staging, production) simply by providing a different `.env` file. It decouples the code from the configuration.
*   **Why PostgreSQL Compatibility?**
    While SQLite is great for development, it is not ideal for a production web application that may handle concurrent requests. PostgreSQL is a powerful, enterprise-grade database. The application is written to work seamlessly with it, ensuring it's ready for a real-world deployment.
*   **Why SQLAlchemy Sessions?**
    Storing sessions in the database is more robust and scalable than using the filesystem, especially in a deployed environment that might use multiple server processes or containers.

In summary, the local version prioritizes a fast and simple developer experience, while the live version prioritizes the best practices required for a secure, scalable, and maintainable web application.

## How to Run This Project Locally (Production Version)

1.  **Clone the Repository and Checkout the `main` branch:**
    ```bash
    git clone <your-repo-url>
    cd EazyBizy_ai_bookeeping
    git checkout main
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create a `.env` File:**
    Create a file named `.env` in the root directory and add the following, replacing the placeholders with your own values:
    ```
    SECRET_KEY='a_very_long_and_random_secret_key'
    DATABASE_URL='sqlite:///instance/ai-bookeeping.db'  # For local SQLite, place it in the instance folder
    # For production, use: DATABASE_URL='postgresql://user:password@host:port/dbname'
    DEEPSEEK_API_KEY='your_openrouter_or_deepseek_api_key'
    MAIL_SERVER='smtp.gmail.com'
    MAIL_PORT=587
    MAIL_USE_TLS=True
    MAIL_USERNAME='your_email@gmail.com'
    MAIL_PASSWORD='your_gmail_app_password'
    ```

5.  **Run the Application:**
    ```bash
    flask run
    ```
    The application will automatically create the database and tables on the first run and will be available at `http://127.0.0.1:5000`.

## Acknowledgments

This project was made possible by the incredible curriculum and supportive community of **CS50**. Thank you to David J. Malan, Brian Yu, and the entire CS50 team for providing the knowledge and inspiration to build something meaningful.
