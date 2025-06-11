# modules/approval/views.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .services import ApprovalAuthorityService
from shared.components import (
    render_status_badge, 
    render_action_buttons,
    render_date_input,
    show_success_message,
    show_error_message,
    show_warning_message,
    confirm_dialog
)
import logging

logger = logging.getLogger(__name__)

class ApprovalAuthorityView:
    """View layer for approval authorities"""
    
    def __init__(self):
        self.service = ApprovalAuthorityService()
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize session state variables"""
        if 'edit_mode' not in st.session_state:
            st.session_state.edit_mode = False
        if 'edit_id' not in st.session_state:
            st.session_state.edit_id = None
        if 'show_add_form' not in st.session_state:
            st.session_state.show_add_form = False
        if 'filters' not in st.session_state:
            st.session_state.filters = {}
    
    def render(self):
        """Main render method"""
        st.title("👥 Approval Authorities Management")
        
        # Action buttons
        col1, col2, col3, col4 = st.columns([1, 1, 1, 5])
        with col1:
            if st.button("➕ Add New", type="primary", use_container_width=True):
                st.session_state.show_add_form = True
                st.session_state.edit_mode = False
                st.session_state.edit_id = None
        
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        st.markdown("---")
        
        # Show add/edit form if needed
        if st.session_state.show_add_form or st.session_state.edit_mode:
            self.render_form()
        else:
            # Show list view
            self.render_list_view()
    
    def render_list_view(self):
        """Render list view with filters"""
        # Filters section
        with st.expander("🔍 Search Filters", expanded=True):
            self.render_filters()
        
        # Get filtered data
        authorities = self.service.get_authorities(st.session_state.filters)
        
        if authorities:
            # Summary stats
            self.render_summary_stats(authorities)
            
            # Data table
            st.subheader(f"Found {len(authorities)} authorities")
            self.render_data_table(authorities)
        else:
            st.info("No authorities found matching the filters.")
    
    def render_filters(self):
        """Render filter controls"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            employees = self.service.get_employees()
            employee_options = {0: "All Employees"}
            employee_options.update({emp['id']: emp['display_name'] for emp in employees})
            
            selected_employee = st.selectbox(
                "Employee",
                options=list(employee_options.keys()),
                format_func=lambda x: employee_options[x],
                key="filter_employee"
            )
            if selected_employee > 0:
                st.session_state.filters['employee_id'] = selected_employee
            elif 'employee_id' in st.session_state.filters:
                del st.session_state.filters['employee_id']
        
        with col2:
            types = self.service.get_approval_types()
            type_options = {0: "All Types"}
            type_options.update({t['id']: t['name'] for t in types})
            
            selected_type = st.selectbox(
                "Approval Type",
                options=list(type_options.keys()),
                format_func=lambda x: type_options[x],
                key="filter_type"
            )
            if selected_type > 0:
                st.session_state.filters['approval_type_id'] = selected_type
            elif 'approval_type_id' in st.session_state.filters:
                del st.session_state.filters['approval_type_id']
        
        with col3:
            companies = self.service.get_companies()
            company_options = {0: "All Companies"}
            company_options.update({c['id']: f"{c['company_code']} - {c['english_name']}" for c in companies})
            
            selected_company = st.selectbox(
                "Company",
                options=list(company_options.keys()),
                format_func=lambda x: company_options[x],
                key="filter_company"
            )
            if selected_company > 0:
                st.session_state.filters['company_id'] = selected_company
            elif 'company_id' in st.session_state.filters:
                del st.session_state.filters['company_id']
        
        with col4:
            status_options = ["All", "Active", "Inactive", "Expired", "Expiring Soon"]
            selected_status = st.selectbox("Status", status_options, key="filter_status")
            if selected_status != "All":
                st.session_state.filters['status'] = selected_status
            elif 'status' in st.session_state.filters:
                del st.session_state.filters['status']
    
    def render_summary_stats(self, authorities: List[Dict]):
        """Render summary statistics"""
        col1, col2, col3, col4 = st.columns(4)
        
        active_count = len([a for a in authorities if a['status'] == 'Active'])
        inactive_count = len([a for a in authorities if a['is_active'] == 0])
        expired_count = len([a for a in authorities if a['status'] == 'Expired'])
        expiring_count = len([a for a in authorities if a['status'] == 'Expiring Soon'])
        
        with col1:
            st.metric("Active", active_count, delta=None)
        with col2:
            st.metric("Inactive", inactive_count, delta=None)
        with col3:
            st.metric("Expired", expired_count, delta=None)
        with col4:
            st.metric("Expiring Soon", expiring_count, delta=None, help="Next 30 days")
    
    def render_data_table(self, authorities: List[Dict]):
        """Render data table with actions"""
        # Create DataFrame for display
        df = pd.DataFrame(authorities)
        
        # Group by employee for better display
        for idx, row in enumerate(authorities):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1.5, 1.5])
                
                with col1:
                    st.markdown(f"**{row['employee_name']}**")
                    st.caption(row['email'])
                
                with col2:
                    st.markdown(f"**{row['approval_type_name']}**")
                    if row['approval_type_code'] == 'PO_SUGGESTION' and row['max_amount']:
                        st.caption(f"Max: ${row['max_amount']:,.0f}")
                
                with col3:
                    if row['company_name']:
                        st.write(row['company_name'])
                    else:
                        st.write("🌍 All Companies")
                
                with col4:
                    # Validity period
                    valid_from = row['valid_from'].strftime('%Y-%m-%d')
                    valid_to = row['valid_to'].strftime('%Y-%m-%d') if row['valid_to'] else 'No Expiry'
                    st.caption(f"{valid_from}")
                    st.caption(f"to {valid_to}")
                
                with col5:
                    # Status and actions
                    status = row['status']
                    if status == 'Active':
                        st.success(status)
                    elif status == 'Inactive':
                        st.error(status)
                    elif status == 'Expired':
                        st.error(status)
                    elif status == 'Expiring Soon':
                        st.warning(status)
                    
                    # Action buttons
                    action_col1, action_col2, action_col3 = st.columns(3)
                    
                    with action_col1:
                        if st.button("✏️", key=f"edit_{row['id']}", help="Edit"):
                            st.session_state.edit_mode = True
                            st.session_state.edit_id = row['id']
                            st.session_state.show_add_form = False
                            st.rerun()
                    
                    with action_col2:
                        if row['is_active']:
                            if st.button("🚫", key=f"deact_{row['id']}", help="Deactivate"):
                                success, message = self.service.toggle_authority_status(row['id'], False)
                                if success:
                                    show_success_message(message)
                                    st.rerun()
                                else:
                                    show_error_message(message)
                        else:
                            if st.button("✅", key=f"act_{row['id']}", help="Activate"):
                                success, message = self.service.toggle_authority_status(row['id'], True)
                                if success:
                                    show_success_message(message)
                                    st.rerun()
                                else:
                                    show_error_message(message)
                    
                    with action_col3:
                        if st.button("🗑️", key=f"del_{row['id']}", help="Delete"):
                            if confirm_dialog(f"delete_{row['id']}"):
                                success, message = self.service.delete_authority(row['id'])
                                if success:
                                    show_success_message(message)
                                    st.rerun()
                                else:
                                    show_error_message(message)
                
                # Notes if any
                if row.get('notes'):
                    st.caption(f"📝 Notes: {row['notes']}")
                
                st.markdown("---")
    
    def render_form(self):
        """Render add/edit form"""
        if st.session_state.edit_mode:
            st.subheader("✏️ Edit Authority")
            authority = self.service.get_authority_by_id(st.session_state.edit_id)
            if not authority:
                show_error_message("Authority not found")
                st.session_state.edit_mode = False
                st.session_state.edit_id = None
                st.rerun()
        else:
            st.subheader("➕ Add New Authority")
            authority = None
        
        with st.form("authority_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Employee selection
                employees = self.service.get_employees()
                employee_options = {emp['id']: emp['display_name'] for emp in employees}
                
                employee_id = st.selectbox(
                    "Employee *",
                    options=list(employee_options.keys()),
                    format_func=lambda x: employee_options[x],
                    index=list(employee_options.keys()).index(authority['employee_id']) if authority else 0
                )
                
                # Approval type selection
                types = self.service.get_approval_types()
                type_options = {t['id']: f"{t['name']} ({t['code']})" for t in types}
                
                approval_type_id = st.selectbox(
                    "Approval Type *",
                    options=list(type_options.keys()),
                    format_func=lambda x: type_options[x],
                    index=list(type_options.keys()).index(authority['approval_type_id']) if authority else 0
                )
                
                # Get selected type code for validation
                selected_type = next((t for t in types if t['id'] == approval_type_id), None)
                approval_type_code = selected_type['code'] if selected_type else None
                
                # Company selection
                companies = self.service.get_companies()
                company_options = {0: "🌍 All Companies"}
                company_options.update({c['id']: f"{c['company_code']} - {c['english_name']}" for c in companies})
                
                company_id = st.selectbox(
                    "Company",
                    options=list(company_options.keys()),
                    format_func=lambda x: company_options[x],
                    index=list(company_options.keys()).index(authority['company_id'] or 0) if authority else 0
                )
            
            with col2:
                # Valid from date
                default_from = authority['valid_from'] if authority else datetime.now().date()
                valid_from = st.date_input("Valid From *", value=default_from)
                
                # Valid to date
                default_to = authority['valid_to'] if authority else None
                valid_to = st.date_input("Valid To (Optional)", value=default_to)
                
                # Max amount for PO approvals
                if approval_type_code == 'PO_SUGGESTION':
                    default_amount = float(authority['max_amount']) if authority and authority.get('max_amount') else 0.0
                    max_amount = st.number_input(
                        "Maximum Amount ($) *",
                        min_value=0.0,
                        value=default_amount,
                        step=1000.0,
                        help="Maximum amount this person can approve for PO"
                    )
                else:
                    max_amount = None
            
            # Notes
            notes = st.text_area(
                "Notes",
                value=authority.get('notes', '') if authority else '',
                help="Additional notes or comments"
            )
            
            # Form buttons
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                submitted = st.form_submit_button(
                    "Update" if st.session_state.edit_mode else "Add",
                    type="primary",
                    use_container_width=True
                )
            with col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)
            
            if submitted:
                # Prepare data
                data = {
                    'employee_id': employee_id,
                    'approval_type_id': approval_type_id,
                    'approval_type_code': approval_type_code,
                    'company_id': company_id if company_id > 0 else None,
                    'valid_from': valid_from,
                    'valid_to': valid_to,
                    'max_amount': max_amount,
                    'notes': notes.strip()
                }
                
                # Save
                if st.session_state.edit_mode:
                    success, message = self.service.update_authority(st.session_state.edit_id, data)
                else:
                    success, message = self.service.add_authority(data)
                
                if success:
                    show_success_message(message)
                    # Reset form state
                    st.session_state.show_add_form = False
                    st.session_state.edit_mode = False
                    st.session_state.edit_id = None
                    st.rerun()
                else:
                    show_error_message(message)
            
            if cancelled:
                # Reset form state
                st.session_state.show_add_form = False
                st.session_state.edit_mode = False
                st.session_state.edit_id = None
                st.rerun()