import os
import json
import logging
from dotenv import load_dotenv

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Detect if running on Streamlit Cloud
def is_running_on_streamlit_cloud():
    try:
        import streamlit as st
        return "DB_CONFIG" in st.secrets
    except Exception:
        return False

IS_RUNNING_ON_CLOUD = is_running_on_streamlit_cloud()

# Load config accordingly
if IS_RUNNING_ON_CLOUD:
    import streamlit as st
    
    DB_CONFIG = dict(st.secrets["DB_CONFIG"])
    EXCHANGE_RATE_API_KEY = st.secrets["API"]["EXCHANGE_RATE_API_KEY"]
    GOOGLE_SERVICE_ACCOUNT_JSON = st.secrets.get("gcp_service_account", {})
    
    logger.info("☁️ Running in STREAMLIT CLOUD")
else:
    load_dotenv()
    
    DB_CONFIG = {
        "host": "erp-all-production.cx1uaj6vj8s5.ap-southeast-1.rds.amazonaws.com",
        "port": 3306,
        "user": "streamlit_user",
        "password": os.getenv("DB_PASSWORD"),
        "database": "prostechvn"
    }
    EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")
    GOOGLE_SERVICE_ACCOUNT_JSON = (
        json.loads(open("credentials.json").read())
        if os.path.exists("credentials.json") else {}
    )
    
    logger.info("💻 Running in LOCAL")