# modules/auth/user_views.py
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from .auth_service import AuthService
from .user_service import UserService
import logging

logger = logging.getLogger(__name__)

class UserManagementView:
    """View layer for user management"""
    
    def __init__(self):
        self.auth_service = AuthService()
        self.user_service = UserService()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables"""
        defaults = {
            'show_user_form': False,
            'edit_user_mode': False,
            'edit_user_id': None,
            'user_filters': {},
            'show_change_password': False
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def render(self):
        """Main render method"""
        st.title("👤 User Management")
        
        # Check permissions
        permissions = st.session_state.get('permissions', {})
        if not permissions.get('can_manage_users', False):
            st.error("❌ You don't have permission to manage users")
            return
        
        # Top action bar
        self._render_action_bar()
        
        # Show form or list based on state
        if st.session_state.show_user_form:
            self._render_user_form()
        elif st.session_state.show_change_password:
            self._render_change_password_form()
        else:
            self._render_user_list()
    
    def _render_action_bar(self):
        """Render top action buttons"""
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 3])
        
        with col1:
            if st.button("➕ Add User", type="primary", use_container_width=True):
                st.session_state.show_user_form = True
                st.session_state.edit_user_mode = False
                st.session_state.edit_user_id = None
                st.rerun()
        
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        with col3:
            if st.button("🔑 Change My Password", use_container_width=True):
                st.session_state.show_change_password = True
                st.rerun()
        
        st.markdown("---")
    
    def _render_user_list(self):
        """Render the user list with filters"""
        # Filters
        with st.expander("🔍 Search Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                username_filter = st.text_input("Username", value=st.session_state.user_filters.get('username', ''))
                if username_filter:
                    st.session_state.user_filters['username'] = username_filter
                else:
                    st.session_state.user_filters.pop('username', None)
            
            with col2:
                role_filter = st.selectbox(
                    "Role",
                    options=['All', 'admin', 'manager', 'user'],
                    index=0
                )
                if role_filter != 'All':
                    st.session_state.user_filters['role'] = role_filter
                else:
                    st.session_state.user_filters.pop('role', None)
            
            with col3:
                status_filter = st.selectbox(
                    "Status",
                    options=['All', 'Active', 'Inactive'],
                    index=0
                )
                if status_filter != 'All':
                    st.session_state.user_filters['is_active'] = 1 if status_filter == 'Active' else 0
                else:
                    st.session_state.user_filters.pop('is_active', None)
        
        # Get users
        users = self.user_service.get_users(st.session_state.user_filters)
        
        if users:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Users", len(users))
            with col2:
                active_users = sum(1 for u in users if u['is_active'])
                st.metric("Active Users", active_users)
            with col3:
                admin_users = sum(1 for u in users if u['role'] == 'admin')
                st.metric("Admins", admin_users)
            with col4:
                recent_logins = sum(1 for u in users if u['last_login'] and 
                                  (datetime.now() - u['last_login']).days < 7)
                st.metric("Recent Logins (7d)", recent_logins)
            
            # User table
            st.subheader(f"Users ({len(users)})")
            self._render_user_table(users)
        else:
            st.info("No users found. Click 'Add User' to create one.")
    
    def _render_user_table(self, users: List[Dict]):
        """Render the user data table"""
        for user in users:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 2])
                
                # User info
                with col1:
                    st.markdown(f"**{user['username']}**")
                    st.caption(user['email'])
                
                # Role & Employee
                with col2:
                    role_emoji = {'admin': '👑', 'manager': '👔', 'user': '👤'}
                    st.write(f"{role_emoji.get(user['role'], '👤')} {user['role'].title()}")
                    if user['full_name']:
                        st.caption(f"Employee: {user['full_name']}")
                
                # Status
                with col3:
                    if user['is_active']:
                        st.success("Active")
                    else:
                        st.error("Inactive")
                
                # Last login
                with col4:
                    if user['last_login']:
                        days_ago = (datetime.now() - user['last_login']).days
                        if days_ago == 0:
                            st.caption("Today")
                        elif days_ago == 1:
                            st.caption("Yesterday")
                        else:
                            st.caption(f"{days_ago} days ago")
                    else:
                        st.caption("Never")
                
                # Actions
                with col5:
                    cols = st.columns(4)
                    
                    # Edit button
                    if cols[0].button("✏️", key=f"edit_user_{user['id']}", help="Edit"):
                        st.session_state.show_user_form = True
                        st.session_state.edit_user_mode = True
                        st.session_state.edit_user_id = user['id']
                        st.rerun()
                    
                    # Reset password
                    if cols[1].button("🔑", key=f"reset_pwd_{user['id']}", help="Reset Password"):
                        if st.checkbox(f"Confirm reset password for {user['username']}?", 
                                     key=f"confirm_reset_{user['id']}"):
                            new_password = self.user_service.reset_password(user['id'])
                            if new_password:
                                st.success(f"Password reset to: `{new_password}`")
                                st.info("Please share this password securely with the user.")
                            else:
                                st.error("Failed to reset password")
                    
                    # Toggle active
                    if user['is_active']:
                        if cols[2].button("🚫", key=f"deact_user_{user['id']}", help="Deactivate"):
                            success, msg = self.user_service.toggle_user_status(user['id'], False)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        if cols[2].button("✅", key=f"act_user_{user['id']}", help="Activate"):
                            success, msg = self.user_service.toggle_user_status(user['id'], True)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    
                    # Delete button (can't delete yourself or last admin)
                    if user['username'] != st.session_state.username:
                        if cols[3].button("🗑️", key=f"del_user_{user['id']}", help="Delete"):
                            if st.checkbox(f"Confirm delete {user['username']}?", 
                                         key=f"confirm_del_user_{user['id']}"):
                                success, msg = self.user_service.delete_user(user['id'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                
                st.markdown("---")
    
    def _render_user_form(self):
        """Render add/edit user form"""
        if st.session_state.edit_user_mode:
            st.subheader("✏️ Edit User")
            user = self.user_service.get_user_by_id(st.session_state.edit_user_id)
            if not user:
                st.error("User not found")
                self._close_form()
                return
        else:
            st.subheader("➕ Add New User")
            user = None
        
        with st.form("user_form"):
            col1, col2 = st.columns(2)
            
            # Username
            with col1:
                if user:
                    st.text_input("Username", value=user['username'], disabled=True)
                    username = user['username']
                else:
                    username = st.text_input("Username *", max_chars=50)
            
            # Email
            with col2:
                email = st.text_input("Email *", value=user['email'] if user else "")
            
            # Password (only for new users)
            if not user:
                col1, col2 = st.columns(2)
                with col1:
                    password = st.text_input("Password *", type="password")
                with col2:
                    confirm_password = st.text_input("Confirm Password *", type="password")
            
            # Role and Employee
            col1, col2 = st.columns(2)
            
            with col1:
                roles = ['user', 'manager', 'admin']
                current_role = user['role'] if user else 'user'
                role = st.selectbox(
                    "Role *",
                    options=roles,
                    index=roles.index(current_role)
                )
            
            with col2:
                # Get employees
                employees = self.user_service.get_available_employees()
                employee_options = {"": "No Employee Link"}
                employee_options.update({
                    str(emp['id']): f"{emp['full_name']} ({emp['email']})"
                    for emp in employees
                })
                
                current_emp = str(user['employee_id']) if user and user['employee_id'] else ""
                employee_id = st.selectbox(
                    "Link to Employee",
                    options=list(employee_options.keys()),
                    format_func=lambda x: employee_options[x],
                    index=list(employee_options.keys()).index(current_emp) if current_emp in employee_options else 0
                )
            
            # Active status
            is_active = st.checkbox("Active", value=user['is_active'] if user else True)
            
            # Form buttons
            col1, col2, col3 = st.columns([1, 1, 4])
            
            with col1:
                submitted = st.form_submit_button(
                    "Update" if user else "Create",
                    type="primary",
                    use_container_width=True
                )
            
            with col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)
            
            if submitted:
                # Validation
                errors = []
                if not username:
                    errors.append("Username is required")
                if not email:
                    errors.append("Email is required")
                if not user:  # New user
                    if not password:
                        errors.append("Password is required")
                    elif password != confirm_password:
                        errors.append("Passwords do not match")
                    elif len(password) < 6:
                        errors.append("Password must be at least 6 characters")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # Save user
                    user_data = {
                        'username': username,
                        'email': email,
                        'role': role,
                        'employee_id': int(employee_id) if employee_id else None,
                        'is_active': is_active
                    }
                    
                    if user:
                        # Update
                        success, msg = self.user_service.update_user(user['id'], user_data)
                    else:
                        # Create
                        user_data['password'] = password
                        success, msg = self.auth_service.create_user(
                            username, password, email, role,
                            int(employee_id) if employee_id else None
                        )
                    
                    if success:
                        st.success(msg)
                        self._close_form()
                    else:
                        st.error(msg)
            
            if cancelled:
                self._close_form()
    
    def _render_change_password_form(self):
        """Render change password form"""
        st.subheader("🔑 Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            col1, col2, col3 = st.columns([1, 1, 4])
            
            with col1:
                submitted = st.form_submit_button("Change", type="primary", use_container_width=True)
            
            with col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)
            
            if submitted:
                if not all([current_password, new_password, confirm_password]):
                    st.error("All fields are required")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    success, msg = self.auth_service.change_password(
                        st.session_state.user_id,
                        current_password,
                        new_password
                    )
                    if success:
                        st.success(msg)
                        st.session_state.show_change_password = False
                        st.rerun()
                    else:
                        st.error(msg)
            
            if cancelled:
                st.session_state.show_change_password = False
                st.rerun()
    
    def _close_form(self):
        """Close form and return to list"""
        st.session_state.show_user_form = False
        st.session_state.edit_user_mode = False
        st.session_state.edit_user_id = None
        st.rerun()