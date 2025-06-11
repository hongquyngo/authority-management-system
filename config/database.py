# config/database.py
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import logging
import streamlit as st
from .config import DB_CONFIG

logger = logging.getLogger(__name__)

@st.cache_resource
def get_db_engine():
    """Create and return SQLAlchemy database engine"""
    logger.info("🔌 Connecting to database...")
    
    user = DB_CONFIG["user"]
    password = quote_plus(str(DB_CONFIG["password"]))
    host = DB_CONFIG["host"]
    port = DB_CONFIG["port"]
    database = DB_CONFIG["database"]
    
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    logger.info(f"🔐 Connecting to: {host}:{port}/{database}")
    
    try:
        engine = create_engine(
            url, 
            pool_pre_ping=True, 
            pool_recycle=3600,
            connect_args={
                "connect_timeout": 10
            }
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return engine
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

def execute_query(query, params=None, fetch=True):
    """Execute database query with SQLAlchemy"""
    engine = get_db_engine()
    
    try:
        with engine.connect() as conn:
            # Convert string query to text object
            if isinstance(query, str):
                query = text(query)
            
            result = conn.execute(query, params or {})
            
            if fetch:
                rows = result.fetchall()
                # Convert rows to list of dicts
                return [dict(row._mapping) for row in rows]
            else:
                conn.commit()
                return result.rowcount
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise