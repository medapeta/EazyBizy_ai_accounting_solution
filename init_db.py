from sqlalchemy import create_engine
from models import Base

engine = create_engine('sqlite:///ai-bookeeping.db', echo=True)  # echo=True prints SQL statements to console

#Base.metadata.drop_all(engine)   # Deletes all tables!
Base.metadata.create_all(engine)  # Recreates them

