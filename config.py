import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "crm360-secret-key"

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///crm360.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False