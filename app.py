# app.py
import streamlit as st
from sqlalchemy import text
from config.settings import APP_CONFIG
from config.database import get_db_engine, execute_query
from modules.approval.views import ApprovalAuthorityView
from modules.auth.auth_service import AuthService
from modules.auth.user_views import UserManagementView
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title=APP_CONFIG['title'],
    page_icon=APP_CONFIG['icon'],
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton > button {
        width: 100%;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff6b6b;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None

def simple_auth():
    """Database authentication form"""
    st.title(f"{APP_CONFIG['icon']} {APP_CONFIG['title']}")
    st.markdown("### Please login to continue")
    
    # Initialize auth service
    auth_service = AuthService()
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns([1, 4])
        
        with col1:
            submitted = st.form_submit_button("Login", type="primary")
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                # Authenticate with database
                success, user_info = auth_service.authenticate_user(username, password)
                
                if success:
                    # Store user info in session
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_id = user_info['id']
                    st.session_state.role = user_info['role']
                    st.session_state.full_name = user_info['full_name']
                    st.session_state.email = user_info['email']
                    st.session_state.employee_id = user_info['employee_id']
                    
                    # Get permissions
                    st.session_state.permissions = auth_service.get_user_permissions(user_info['role'])
                    
                    st.success("Login successful!")
                    st.rerun()
                else:
                    if user_info and 'error' in user_info:
                        st.error(user_info['error'])
                    else:
                        st.error("Invalid username or password")
    
    
    # Show connection status
    st.sidebar.markdown("---")
    st.sidebar.caption("Database Connection Status")
    success, message = test_database_connection()
    if success:
        st.sidebar.success("✅ Connected")
    else:
        st.sidebar.error("❌ Disconnected")

def render_sidebar():
    """Render sidebar navigation"""
    with st.sidebar:
        st.title(f"{APP_CONFIG['icon']} {APP_CONFIG['title']}")
        st.markdown("---")
        
        # Module selection
        enabled_modules = {k: v for k, v in APP_CONFIG['modules'].items() if v['enabled']}
        
        if not enabled_modules:
            st.error("No modules enabled")
            return None
        
        module_names = list(enabled_modules.keys())
        module_labels = [f"{v['icon']} {v['name']}" for v in enabled_modules.values()]
        
        selected_idx = st.radio(
            "Select Module",
            range(len(module_names)),
            format_func=lambda x: module_labels[x]
        )
        
        selected_module = module_names[selected_idx]
        
        # Module description
        st.info(enabled_modules[selected_module].get('description', ''))
        
        # User info
        st.markdown("---")
        st.markdown("**User Information**")
        st.info(f"👤 {st.session_state.get('full_name', st.session_state.username)}")
        st.caption(f"Role: {st.session_state.role}")
        st.caption(f"Email: {st.session_state.get('email', 'N/A')}")
        
        # Quick stats - with error handling
        st.markdown("---")
        st.markdown("**Quick Stats**")
        try:
            # Active authorities count
            query = """
            SELECT COUNT(DISTINCT employee_id) as count
            FROM approval_authorities
            WHERE is_active = 1 AND delete_flag = 0
            AND (valid_to IS NULL OR valid_to >= CURDATE())
            """
            result = execute_query(query)
            active_count = result[0]['count'] if result else 0
            st.metric("Active Approvers", active_count)
            
            # Expiring soon count
            query = """
            SELECT COUNT(*) as count
            FROM approval_authorities
            WHERE is_active = 1 AND delete_flag = 0
            AND valid_to BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            """
            result = execute_query(query)
            expiring_count = result[0]['count'] if result else 0
            if expiring_count > 0:
                st.warning(f"⚠️ {expiring_count} authorities expiring soon")
        except Exception as e:
            logger.error(f"Error loading sidebar stats: {e}")
            st.caption("Stats unavailable")
        
        # Logout button
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for key in ['logged_in', 'username', 'role']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    return selected_module

def test_database_connection():
    """Test database connection"""
    try:
        result = execute_query("SELECT 1 as test")
        if result is not None:
            return True, "Database connection successful"
        else:
            return False, "Database query returned no results"
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return False, f"Database connection failed: {str(e)}"

def main():
    """Main application"""
    initialize_session_state()
    
    # Check authentication
    if not st.session_state.get('logged_in'):
        simple_auth()
        return
    
    # Test database connection
    success, message = test_database_connection()
    if not success:
        st.error(f"❌ {message}")
        st.info("Please check your database configuration and try again.")
        if st.button("Retry Connection"):
            st.rerun()
        return
    
    # Render navigation
    selected_module = render_sidebar()
    
    if not selected_module:
        st.error("No module selected")
        return
    
    # Route to module
    if selected_module == 'approval':
        view = ApprovalAuthorityView()
        view.render()
    elif selected_module == 'users':
        # Check if user has permission
        permissions = st.session_state.get('permissions', {})
        if permissions.get('can_manage_users', False):
            view = UserManagementView()
            view.render()
        else:
            st.error("❌ You don't have permission to access User Management")
            st.info("Please contact your administrator for access.")
    else:
        # Placeholder for other modules
        st.title(f"{APP_CONFIG['modules'][selected_module]['icon']} {APP_CONFIG['modules'][selected_module]['name']}")
        st.info(f"The {APP_CONFIG['modules'][selected_module]['name']} module is not yet implemented.")
        st.markdown("""
        ### Coming Soon
        This module will allow you to:
        - Define data access rules
        - Control who can view what data
        - Set up hierarchical access permissions
        - Manage time-based access controls
        """)
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.caption(f"Version {APP_CONFIG['version']} | © 2024 Authority Management System")

if __name__ == "__main__":
    main()