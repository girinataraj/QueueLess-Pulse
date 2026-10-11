import os
import secrets
from dotenv import load_dotenv
load_dotenv()
class Config:
    APP_STAGE = os.getenv('APP_STAGE', '')
    STAGING_DATABASE_NAME = os.getenv('STAGING_DATABASE_NAME', '')
    PRODUCTION = os.getenv('APP_ENV') == 'production' or bool(os.getenv('RENDER'))
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///dev.db').replace('postgres://', 'postgresql+psycopg2://', 1).replace('postgresql://', 'postgresql+psycopg2://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = PRODUCTION
    BUSINESS_TIMEZONE = os.getenv('BUSINESS_TIMEZONE', 'Asia/Kolkata')
    AVERAGE_SERVICE_TIME_MINUTES = int(os.getenv('AVERAGE_SERVICE_TIME_MINUTES', '5'))
    MAX_CONTENT_LENGTH = 16384
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
    TRUSTED_HOSTS = [host.strip() for host in os.getenv('TRUSTED_HOSTS','').split(',') if host.strip()] or None
    RATE_LIMIT_AUTH = int(os.getenv('RATE_LIMIT_AUTH', '30'))
    RATE_LIMIT_GATEWAY = int(os.getenv('RATE_LIMIT_GATEWAY', '30'))
    RATE_LIMIT_QUEUE = int(os.getenv('RATE_LIMIT_QUEUE', '120'))
    RATE_LIMIT_TRUSTED_PROXY_HOPS = int(os.getenv('RATE_LIMIT_TRUSTED_PROXY_HOPS', '0'))
    DEMO_MODE = os.getenv('DEMO_MODE', 'false').lower() == 'true'
    STAGING_AUTH_MODE = os.getenv('STAGING_AUTH_MODE', 'basic')
    OWNER_REGISTRATION_ENABLED = os.getenv('OWNER_REGISTRATION_ENABLED', 'false' if APP_STAGE == 'staging' else 'true').lower() == 'true'
    DEMO_ACCESS_USER = os.getenv('DEMO_ACCESS_USER', '')
    DEMO_ACCESS_PASSWORD = os.getenv('DEMO_ACCESS_PASSWORD', '')
