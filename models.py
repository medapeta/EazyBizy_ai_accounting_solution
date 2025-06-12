from extension import db  # Import the Flask-SQLAlchemy instance
from datetime import datetime

class users_db(db.Model):
    __tablename__ = 'users_db'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    bussiness_name = db.Column(db.String, unique=True, nullable=False)
    currency = db.Column(db.String, default='USD')
    fiscal_year_start = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    accounts = db.relationship('chart_of_accounts_db', back_populates='user',cascade="all, delete-orphan")
    transactions = db.relationship('transactions_db', back_populates='user',cascade="all, delete-orphan")

class chart_of_accounts_db(db.Model):
    __tablename__ = 'chart_of_accounts_db'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users_db.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    normal_side = db.Column(db.String, nullable=False)
    code = db.Column(db.String, nullable=True)
    opening_balance = db.Column(db.Numeric(12, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('users_db', back_populates='accounts')
    transaction_lines = db.relationship("transaction_detail_db", back_populates="account")


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
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    is_debit = db.Column(db.Boolean, default=False)
    
    transaction = db.relationship("transactions_db", back_populates="details")
    account = db.relationship("chart_of_accounts_db", back_populates="transaction_lines")
