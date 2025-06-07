# extensions.py
# this will be a bridge between app.py and models.py and remove the circular import problem
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # Initialize db separately