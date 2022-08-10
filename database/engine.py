import os

from sqlmodel import SQLModel, create_engine

from database.models import *

__all__ = ["engine"]

pguser = os.environ.get("POSTGRES_USER", "postgres")
passwd = os.environ.get("POSTGRES_PASSWORD", "password")
pghost = os.environ.get("POSTGRES_HOST", "postgres")
db = os.environ.get("POSTGRES_DATABASE", "postgres")

database_uri = f"postgresql://{pguser}:{passwd}@{pghost}:5432/{db}"
engine = create_engine(database_uri)
SQLModel.metadata.create_all(engine)
