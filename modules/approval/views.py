# modules/approval/views.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .services import ApprovalAuthorityService
import logging

logger = logging.getLogger(__name__)

class ApprovalAuthorityView:
    """View layer for approval authorities management"""
    
    def __init__(self):
        self.service = ApprovalAuthorityService()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables"""
        defaults = {
            'show_form': False,
            'edit_mode': False,
            'edit_id': None,
            'filters': {},
            'page': 0,
            'page_size': 20,
            'delete_confirmations': {}
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def render(self):
        """Main render method"""
        st.title("👥 Approval Authorities Management")
        
        # Top action bar
        self._render_action_bar()
        
        # Show form or list based on state
        if st.session_state.show_form:
            self._render_form()
        else:
            self._render_list_view()
    
    def _render_action_bar(self):
        """Render top action buttons"""
        col1, col2, col3, col4 = st.columns([1, 1, 1, 5])
        
        with col1:
            if st.button("➕ Add New", type="primary", use_container_width=True):
                st.session_state.show_form = True
                st.session_state.edit_mode = False
                st.session_state.edit_id = None
                st.rerun()
        
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                # Clear pagination
                st.session_state.page = 0
                st.rerun()
        
        st.markdown("---")
    
    def _render_list_view(self):
        """Render the list view with filters and data table"""
        # Filters
        with st.expander("🔍 Search Filters", expanded=True):
            self._render_filters()
        
        # Get data with pagination
        offset = st.session_state.page * st.session_state.page_size
        authorities = self.service.get_authorities(
            st.session_state.filters, 
            limit=st.session_state.page_size + 1,  # Get one extra to check if there's next page
            offset=offset
        )
        
        # Check if there's a next page
        has_next = len(authorities) > st.session_state.page_size
        if has_next:
            authorities = authorities[:-1]  # Remove the extra item
        
        if authorities:
            # Summary metrics
            self._render_summary_metrics(authorities)
            
            # Data table with pagination
            st.subheader(f"Authorities (Page {st.session_state.page + 1})")
            self._render_data_table(authorities)
            
            # Pagination controls
            self._render_pagination(has_next)
        else:
            if st.session_state.page > 0:
                # Go back to first page if current page has no data
                st.session_state.page = 0
                st.rerun()
            else:
                st.info("No authorities found. Click 'Add New' to create one.")
    
    def _render_pagination(self, has_next: bool):
        """Render pagination controls"""
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.button("⬅️ Previous", disabled=st.session_state.page == 0):
                st.session_state.page -= 1
                st.rerun()
        
        with col2:
            st.markdown(f"<center>Page {st.session_state.page + 1}</center>", unsafe_allow_html=True)
        
        with col3:
            if st.button("Next ➡️", disabled=not has_next):
                st.session_state.page += 1
                st.rerun()
    
    def _render_filters(self):
        """Render filter controls"""
        col1, col2, col3, col4 = st.columns(4)
        
        # Employee filter
        with col1:
            employees = self.service.get_employees()
            employee_options = {"": "All Employees"}
            employee_options.update({
                str(emp['id']): f"{emp['full_name']} ({emp['email']})"
                for emp in employees
            })
            
            current_value = str(st.session_state.filters.get('employee_id', ''))
            selected = st.selectbox(
                "Employee",
                options=list(employee_options.keys()),
                index=list(employee_options.keys()).index(current_value) if current_value in employee_options else 0,
                format_func=lambda x: employee_options[x]
            )
            
            if selected:
                st.session_state.filters['employee_id'] = int(selected)
            else:
                st.session_state.filters.pop('employee_id', None)
        
        # Approval Type filter
        with col2:
            types = self.service.get_approval_types()
            type_options = {"": "All Types"}
            type_options.update({
                str(t['id']): t['name'] for t in types
            })
            
            current_value = str(st.session_state.filters.get('approval_type_id', ''))
            selected = st.selectbox(
                "Approval Type",
                options=list(type_options.keys()),
                index=list(type_options.keys()).index(current_value) if current_value in type_options else 0,
                format_func=lambda x: type_options[x]
            )
            
            if selected:
                st.session_state.filters['approval_type_id'] = int(selected)
            else:
                st.session_state.filters.pop('approval_type_id', None)
        
        # Company filter
        with col3:
            companies = self.service.get_companies()
            company_options = {"": "All Companies"}
            company_options.update({
                str(c['id']): f"{c['company_code']} - {c['english_name']}"
                for c in companies
            })
            
            current_value = str(st.session_state.filters.get('company_id', ''))
            selected = st.selectbox(
                "Company",
                options=list(company_options.keys()),
                index=list(company_options.keys()).index(current_value) if current_value in company_options else 0,
                format_func=lambda x: company_options[x]
            )
            
            if selected:
                st.session_state.filters['company_id'] = int(selected)
            else:
                st.session_state.filters.pop('company_id', None)
        
        # Status filter
        with col4:
            current_status = st.session_state.filters.get('status', 'All')
            status = st.selectbox(
                "Status",
                options=["All", "Active", "Inactive", "Expired", "Expiring Soon"],
                index=["All", "Active", "Inactive", "Expired", "Expiring Soon"].index(current_status)
            )
            
            if status != "All":
                st.session_state.filters['status'] = status
            else:
                st.session_state.filters.pop('status', None)
        
        # Reset page when filters change
        st.session_state.page = 0
    
    def _render_summary_metrics(self, authorities: List[Dict]):
        """Render summary statistics for current page"""
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate counts for current page with bytes handling
        active = 0
        inactive = 0
        expired = 0
        expiring = 0
        
        for a in authorities:
            # Handle bytes type for is_active
            is_active_raw = a.get('is_active', 0)
            if isinstance(is_active_raw, bytes):
                is_active = int.from_bytes(is_active_raw, byteorder='big')
            else:
                is_active = int(is_active_raw) if is_active_raw is not None else 0
            
            if a['status'] == 'Active':
                active += 1
            elif a['status'] == 'Inactive' or is_active == 0:
                inactive += 1
            elif a['status'] == 'Expired':
                expired += 1
            elif a['status'] == 'Expiring Soon':
                expiring += 1
        
        with col1:
            st.metric("Active", active)
        with col2:
            st.metric("Inactive", inactive)
        with col3:
            st.metric("Expired", expired)
        with col4:
            st.metric("Expiring Soon", expiring, help="Next 30 days")
    
    def _convert_is_active(self, is_active_raw):
        """Convert is_active from various types to boolean"""
        if isinstance(is_active_raw, bytes):
            # Handle bytes type from MySQL
            return int.from_bytes(is_active_raw, byteorder='big') == 1
        elif isinstance(is_active_raw, (int, float)):
            return int(is_active_raw) == 1
        elif isinstance(is_active_raw, str):
            return is_active_raw == '1'
        else:
            return False
    
    def _render_data_table(self, authorities: List[Dict]):
        """Render the data table with actions"""
        for auth in authorities:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1.5, 1.5])
                
                # Employee info
                with col1:
                    st.markdown(f"**{auth['employee_name']}**")
                    st.caption(auth['email'])
                
                # Approval type
                with col2:
                    st.markdown(f"**{auth['approval_type_name']}**")
                    if auth.get('max_amount'):
                        st.caption(f"Max: ${auth['max_amount']:,.0f}")
                
                # Company
                with col3:
                    if auth['company_name']:
                        st.write(auth['company_name'])
                    else:
                        st.write("🌍 All Companies")
                
                # Validity
                with col4:
                    valid_from = auth['valid_from'].strftime('%Y-%m-%d')
                    valid_to = auth['valid_to'].strftime('%Y-%m-%d') if auth['valid_to'] else 'No Expiry'
                    st.caption(f"From: {valid_from}")
                    st.caption(f"To: {valid_to}")
                
                # Status & Actions
                with col5:
                    # Status badge
                    self._render_status_badge(auth['status'])
                    
                    # Action buttons
                    cols = st.columns(3)
                    
                    # Edit button
                    if cols[0].button("✏️", key=f"edit_{auth['id']}", help="Edit"):
                        st.session_state.show_form = True
                        st.session_state.edit_mode = True
                        st.session_state.edit_id = auth['id']
                        st.rerun()
                    
                    # Toggle active/inactive - with proper bytes handling
                    is_active = self._convert_is_active(auth.get('is_active', 0))
                    
                    if is_active:
                        if cols[1].button("🚫", key=f"deact_{auth['id']}", help="Deactivate"):
                            self._toggle_status(auth['id'], False)
                    else:
                        if cols[1].button("✅", key=f"act_{auth['id']}", help="Activate"):
                            self._toggle_status(auth['id'], True)
                    
                    # Delete button
                    if cols[2].button("🗑️", key=f"del_{auth['id']}", help="Delete"):
                        st.session_state.delete_confirmations[auth['id']] = True
                        st.rerun()
                
                # Show delete confirmation if needed
                if st.session_state.delete_confirmations.get(auth['id']):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.warning("⚠️ Are you sure you want to delete this authority?")
                    with col2:
                        if st.button("Confirm", key=f"confirm_del_{auth['id']}", type="primary"):
                            self._delete_authority(auth['id'])
                            del st.session_state.delete_confirmations[auth['id']]
                        if st.button("Cancel", key=f"cancel_del_{auth['id']}"):
                            del st.session_state.delete_confirmations[auth['id']]
                            st.rerun()
                
                # Notes
                if auth.get('notes'):
                    st.caption(f"📝 {auth['notes']}")
                
                st.markdown("---")
    
    def _render_form(self):
        """Render the add/edit form"""
        # Form header
        if st.session_state.edit_mode:
            st.subheader("✏️ Edit Authority")
            # Load existing data
            authority = self.service.get_authority_by_id(st.session_state.edit_id)
            if not authority:
                st.error("Authority not found")
                self._close_form()
                return
        else:
            st.subheader("➕ Add New Authority")
            authority = None
        
        # Form
        with st.form("authority_form", clear_on_submit=False):
            # Employee selection
            st.markdown("#### 1️⃣ Select Employee")
            employees = self.service.get_employees()
            if not employees:
                st.error("No employees found in the system")
                st.form_submit_button("Cancel")
                self._close_form()
                return
                
            employee_map = {
                emp['id']: f"{emp['full_name']} ({emp['email']})"
                for emp in employees
            }
            
            default_emp = authority['employee_id'] if authority else list(employee_map.keys())[0]
            employee_id = st.selectbox(
                "Employee *",
                options=list(employee_map.keys()),
                format_func=lambda x: employee_map[x],
                index=list(employee_map.keys()).index(default_emp) if default_emp in employee_map else 0
            )
            
            # Approval Type selection
            st.markdown("#### 2️⃣ Select Approval Type(s)")
            types = self.service.get_approval_types()
            if not types:
                st.error("No approval types found in the system")
                st.form_submit_button("Cancel")
                self._close_form()
                return
                
            type_map = {t['id']: f"{t['name']} ({t['code']})" for t in types}
            
            if st.session_state.edit_mode:
                # Single select for edit mode
                default_type = authority['approval_type_id'] if authority else list(type_map.keys())[0]
                type_id = st.selectbox(
                    "Approval Type *",
                    options=list(type_map.keys()),
                    format_func=lambda x: type_map[x],
                    index=list(type_map.keys()).index(default_type) if default_type in type_map else 0
                )
                selected_types = [type_id]
            else:
                # Multi-select for create mode
                selected_types = st.multiselect(
                    "Approval Types *",
                    options=list(type_map.keys()),
                    format_func=lambda x: type_map[x],
                    help="Select one or more approval types"
                )
            
            # Company selection
            st.markdown("#### 3️⃣ Select Company(ies)")
            companies = self.service.get_companies()
            
            # Add "All Companies" option
            company_map = {0: "🌍 All Companies"}
            if companies:
                for c in companies:
                    company_map[c['id']] = f"{c['company_code']} - {c['english_name']}"
            
            if st.session_state.edit_mode:
                # Single select for edit mode
                default_comp = authority.get('company_id', 0) if authority else 0
                company_id = st.selectbox(
                    "Company",
                    options=list(company_map.keys()),
                    format_func=lambda x: company_map[x],
                    index=list(company_map.keys()).index(default_comp or 0)
                )
                selected_companies = [None if company_id == 0 else company_id]
            else:
                # Multi-select for create mode
                selected_company_ids = st.multiselect(
                    "Companies",
                    options=list(company_map.keys()),
                    format_func=lambda x: company_map[x],
                    help="Select companies or leave empty for ALL companies",
                    default=[]
                )
                
                # If nothing selected or "All Companies" (0) is selected, means all companies
                if not selected_company_ids or 0 in selected_company_ids:
                    selected_companies = [None]
                    st.info("✅ Will grant authority for ALL companies")
                else:
                    selected_companies = selected_company_ids
                    st.success(f"✅ Selected {len(selected_companies)} specific companies")
            
            # Validity period
            st.markdown("#### 4️⃣ Set Validity Period")
            col1, col2 = st.columns(2)
            
            with col1:
                default_from = authority['valid_from'] if authority else datetime.now().date()
                valid_from = st.date_input("Valid From *", value=default_from)
            
            with col2:
                default_to = authority['valid_to'] if authority else (datetime.now().date() + timedelta(days=365))
                valid_to = st.date_input("Valid To", value=default_to)
            
            # Max amount (conditional)
            selected_type_codes = [t['code'] for t in types if t['id'] in selected_types]
            requires_amount = any(code in ['PO_SUGGESTION', 'PO_CANCELLATION', 'OC_CANCELLATION', 'OC_RETURN'] 
                                for code in selected_type_codes)
            
            if requires_amount:
                st.markdown("#### 5️⃣ Set Amount Limit")
                if authority:
                    # Handle None value from database
                    default_amount = authority.get('max_amount', 10000.0)
                    if default_amount is None:
                        default_amount = 10000.0
                else:
                    default_amount = 10000.0
                    
                max_amount = st.number_input(
                    "Maximum Amount ($) *",
                    min_value=0.0,
                    max_value=999999999.0,
                    value=float(default_amount),
                    step=1000.0
                )
            else:
                max_amount = None
            
            # Notes
            st.markdown("#### 6️⃣ Additional Notes")
            default_notes = authority.get('notes', '') if authority else ''
            notes = st.text_area("Notes (Optional)", value=default_notes, max_chars=500)
            
            # Summary for create mode
            if not st.session_state.edit_mode and selected_types:
                st.markdown("---")
                st.markdown("### 📊 Summary")
                
                # Calculate total authorities to create
                total = len(selected_types) * len(selected_companies)
                st.info(f"""
                **Total Authorities to Create:** {total}
                - Employee: {employee_map[employee_id]}
                - Approval Types: {len(selected_types)}
                - Companies: {len(selected_companies)} {'(All)' if selected_companies == [None] else ''}
                """)
            
            # Form buttons
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 4])
            
            with col1:
                submitted = st.form_submit_button(
                    "Save" if st.session_state.edit_mode else "Create",
                    type="primary",
                    use_container_width=True
                )
            
            with col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)
            
            # Process form submission
            if submitted:
                # Validation
                if not selected_types:
                    st.error("Please select at least one approval type")
                    return
                
                if st.session_state.edit_mode:
                    # Single update
                    self._process_single_save(
                        st.session_state.edit_id,
                        employee_id,
                        selected_types[0],
                        selected_companies[0],
                        valid_from,
                        valid_to,
                        max_amount,
                        notes
                    )
                else:
                    # Batch create
                    self._process_batch_create(
                        employee_id,
                        selected_types,
                        selected_companies,
                        valid_from,
                        valid_to,
                        max_amount,
                        notes
                    )
            
            if cancelled:
                self._close_form()
    
    def _render_status_badge(self, status: str):
        """Render status badge with appropriate color"""
        if status == 'Active':
            st.success(status)
        elif status in ['Inactive', 'Expired']:
            st.error(status)
        elif status == 'Expiring Soon':
            st.warning(status)
        else:
            st.info(status)
    
    def _toggle_status(self, authority_id: int, activate: bool):
        """Toggle authority active status"""
        success, message = self.service.toggle_authority_status(authority_id, activate)
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)
    
    def _delete_authority(self, authority_id: int):
        """Delete authority"""
        success, message = self.service.delete_authority(authority_id)
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)
    
    def _process_single_save(self, authority_id, employee_id, type_id, company_id, 
                           valid_from, valid_to, max_amount, notes):
        """Process single authority save (create or update)"""
        # Get type info for validation
        types = self.service.get_approval_types()
        type_info = next((t for t in types if t['id'] == type_id), None)
        
        data = {
            'employee_id': employee_id,
            'approval_type_id': type_id,
            'approval_type_code': type_info['code'] if type_info else None,
            'company_id': company_id,
            'valid_from': valid_from,
            'valid_to': valid_to,
            'max_amount': max_amount,
            'notes': notes.strip()
        }
        
        if authority_id:
            # Update
            success, message = self.service.update_authority(authority_id, data)
        else:
            # Create
            success, message = self.service.add_authority(data)
        
        if success:
            st.success(message)
            self._close_form()
        else:
            st.error(message)
    
    def _process_batch_create(self, employee_id, type_ids, company_ids, 
                            valid_from, valid_to, max_amount, notes):
        """Process batch creation of authorities"""
        if not type_ids or not company_ids:
            st.error("Please select at least one approval type and company")
            return
        
        # Get types info
        types = self.service.get_approval_types()
        types_dict = {t['id']: t for t in types}
        
        # Progress tracking
        total = len(type_ids) * len(company_ids)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        success_count = 0
        errors = []
        
        # Process each combination
        for i, type_id in enumerate(type_ids):
            type_info = types_dict.get(type_id, {})
            
            for j, company_id in enumerate(company_ids):
                current = i * len(company_ids) + j + 1
                progress = current / total
                progress_bar.progress(progress)
                
                status_text.text(f"Processing {current}/{total}...")
                
                data = {
                    'employee_id': employee_id,
                    'approval_type_id': type_id,
                    'approval_type_code': type_info.get('code'),
                    'company_id': company_id,
                    'valid_from': valid_from,
                    'valid_to': valid_to,
                    'max_amount': max_amount if type_info.get('code') in ['PO_SUGGESTION', 'PO_CANCELLATION', 'OC_CANCELLATION', 'OC_RETURN'] else None,
                    'notes': notes.strip()
                }
                
                success, message = self.service.add_authority(data)
                if success:
                    success_count += 1
                else:
                    company_name = "All Companies" if company_id is None else f"Company {company_id}"
                    errors.append(f"{type_info.get('name', 'Unknown')} - {company_name}: {message}")
        
        # Clear progress
        progress_bar.empty()
        status_text.empty()
        
        # Show results
        if success_count > 0:
            st.success(f"✅ Successfully created {success_count} authorities")
        
        if errors:
            with st.expander(f"❌ {len(errors)} errors occurred", expanded=True):
                for error in errors:
                    st.error(error)
        
        if success_count > 0:
            self._close_form()
    
    def _close_form(self):
        """Close the form and return to list view"""
        st.session_state.show_form = False
        st.session_state.edit_mode = False
        st.session_state.edit_id = None
        st.session_state.delete_confirmations = {}
        st.rerun()