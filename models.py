from app import db  # Import the Flask-SQLAlchemy instance
from datetime import datetime

class users_db(db.Model):
    __tablename__ = 'users_db'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    bussiness_name = db.Column(db.String, unique=True, nullable=False)
    logo_path = db.Column(db.String, nullable=True)
    currency = db.Column(db.String, default='USD')
    fiscal_year_start = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    accounts = db.relationship('chart_of_accounts_db', back_populates='user')
    categories = db.relationship('categories_db', back_populates='user')
    transactions = db.relationship('transactions_db', back_populates='user')

class chart_of_accounts_db(db.Model):
    __tablename__ = 'chart_of_accounts_db'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_db.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    normal_side = db.Column(db.String, nullable=False)
    code = db.Column(db.String, nullable=True)
    opening_balance = db.Column(db.Numeric(12, 2), default=0.00)
    is_system_account = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('users_db', back_populates='accounts')
    transaction_lines = db.relationship("transaction_detail_db", back_populates="account")

class categories_db(db.Model):
    __tablename__ = 'categories_db'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_db.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    parent_category_id = db.Column(db.Integer, db.ForeignKey('categories_db.id'), nullable=True)

    user = db.relationship('users_db', back_populates='categories')
    parent_category = db.relationship('categories_db', remote_side=[id])
    transaction_lines = db.relationship("transaction_detail_db", back_populates="category")

class transactions_db(db.Model):
    __tablename__ = 'transactions_db'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_db.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String)
    reference_number = db.Column(db.String, nullable=True)
    is_archived = db.Column(db.Boolean, default=False)

    user = db.relationship('users_db', back_populates='transactions')
    details = db.relationship("transaction_detail_db", back_populates="transaction", cascade="all, delete-orphan")

class transaction_detail_db(db.Model):
    __tablename__ = 'transaction_detail_db'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions_db.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts_db.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories_db.id'), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    is_debit = db.Column(db.Boolean, default=False)
    
    transaction = db.relationship("transactions_db", back_populates="details")
    account = db.relationship("chart_of_accounts_db", back_populates="transaction_lines")
    category = db.relationship("categories_db", back_populates="transaction_lines")