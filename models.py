from sqlalchemy import (
    create_engine, Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class users_db(Base):
    __tablename__ = 'users_db'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    bussiness_name = Column(String, unique=True, nullable=False)
    currency = Column(String, default='USD')
    fiscal_year_start = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    accounts = relationship('chart_of_accounts_db', back_populates='user',cascade="all, delete-orphan")
    categories = relationship('categories_db', back_populates='user',cascade="all, delete-orphan")
    transactions = relationship('transactions_db', back_populates='user',cascade="all, delete-orphan")


class chart_of_accounts_db(Base):
    __tablename__ = 'chart_of_accounts_db'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users_db.id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # e.g. Asset, Liability, etc.
    normal_side = Column(String, nullable=False) # debit or credit
    code = Column(String, nullable=True)
    opening_balance = Column(Numeric(12, 2), default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('users_db', back_populates='accounts')
    transaction_lines = relationship("transaction_detail_db", back_populates="account")


class categories_db(Base):
    __tablename__ = 'categories_db'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users_db.id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # Income/Expense/Tax
    parent_category_id = Column(Integer, ForeignKey('categories_db.id'), nullable=True)
    #tax_rate_id = Column(Integer, ForeignKey('tax_rates_db.id'), nullable=True)

    user = relationship('users_db', back_populates='categories')
    parent_category = relationship('categories_db', remote_side=[id])
    transaction_lines = relationship("transaction_detail_db", back_populates="category")


class transactions_db(Base):
    __tablename__ = 'transactions_db'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users_db.id'), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    description = Column(String)
    reference_number = Column(String, nullable=True)
    is_archived = Column(Boolean, default=False)

    user = relationship('users_db', back_populates='transactions')
    details = relationship("transaction_detail_db", back_populates="transaction", cascade="all, delete-orphan")


class transaction_detail_db(Base):
    __tablename__ = 'transaction_detail_db'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transactions_db.id'), nullable=False)
    account_id = Column(Integer, ForeignKey('chart_of_accounts_db.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories_db.id'), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)  # Positive = Debit, Negative = Credit
    #tax_rate_id = Column(Integer, ForeignKey('tax_rates_db.id'), nullable=True)
    is_debit = Column(Boolean, default=False)
    
    # 🔗 Relationships
    transaction = relationship("transactions_db", back_populates="details")
    account = relationship("chart_of_accounts_db", back_populates="transaction_lines")
    category = relationship("categories_db", back_populates="transaction_lines")
    #tax_rate = relationship("tax_rates_db", back_populates="transaction_lines")
