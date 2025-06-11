# shared/components.py
import streamlit as st
from datetime import datetime
from typing import Any, Dict, List, Optional

def render_status_badge(status: str) -> None:
    """Render a status badge with appropriate styling"""
    if status == 'Active':
        st.success(status)
    elif status in ['Inactive', 'Expired']:
        st.error(status)
    elif status == 'Expiring Soon':
        st.warning(status)
    else:
        st.info(status)

def render_action_buttons(actions: List[str], record_id: int, callbacks: Dict) -> None:
    """Render action buttons for a record"""
    cols = st.columns(len(actions))
    
    for idx, action in enumerate(actions):
        with cols[idx]:
            if action == 'edit':
                if st.button("✏️", key=f"edit_{record_id}", help="Edit"):
                    if 'edit' in callbacks:
                        callbacks['edit'](record_id)
            elif action == 'delete':
                if st.button("🗑️", key=f"delete_{record_id}", help="Delete"):
                    if 'delete' in callbacks:
                        callbacks['delete'](record_id)
            elif action == 'toggle':
                if st.button("🔄", key=f"toggle_{record_id}", help="Toggle Status"):
                    if 'toggle' in callbacks:
                        callbacks['toggle'](record_id)

def render_date_input(label: str, value: Optional[datetime] = None, 
                     min_date: Optional[datetime] = None,
                     max_date: Optional[datetime] = None) -> datetime:
    """Render a date input with validation"""
    return st.date_input(
        label,
        value=value or datetime.now(),
        min_value=min_date,
        max_value=max_date
    )

def show_success_message(message: str) -> None:
    """Display a success message"""
    st.success(f"✅ {message}")

def show_error_message(message: str) -> None:
    """Display an error message"""
    st.error(f"❌ {message}")

def show_warning_message(message: str) -> None:
    """Display a warning message"""
    st.warning(f"⚠️ {message}")

def show_info_message(message: str) -> None:
    """Display an info message"""
    st.info(f"ℹ️ {message}")

def confirm_dialog(key: str, message: str = "Are you sure?") -> bool:
    """Show a confirmation dialog"""
    return st.checkbox(message, key=f"confirm_{key}")

def render_metric_card(title: str, value: Any, delta: Optional[Any] = None,
                      delta_color: str = "normal", help_text: Optional[str] = None) -> None:
    """Render a metric card"""
    st.metric(
        label=title,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )

def render_data_table_with_pagination(data: List[Dict], page_size: int = 10) -> None:
    """Render a data table with pagination"""
    total_pages = len(data) // page_size + (1 if len(data) % page_size > 0 else 0)
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    # Pagination controls
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.button("◀️ Previous", disabled=st.session_state.current_page == 1):
            st.session_state.current_page -= 1
    
    with col2:
        st.markdown(f"<center>Page {st.session_state.current_page} of {total_pages}</center>", 
                   unsafe_allow_html=True)
    
    with col3:
        if st.button("Next ▶️", disabled=st.session_state.current_page == total_pages):
            st.session_state.current_page += 1
    
    # Display current page data
    start_idx = (st.session_state.current_page - 1) * page_size
    end_idx = min(start_idx + page_size, len(data))
    
    return data[start_idx:end_idx]

def render_search_bar(placeholder: str = "Search...") -> str:
    """Render a search bar"""
    return st.text_input("🔍 Search", placeholder=placeholder, label_visibility="collapsed")

def render_export_button(data: Any, filename: str = "export.csv") -> None:
    """Render an export button for data"""
    if st.button("📥 Export to CSV"):
        csv = data.to_csv(index=False) if hasattr(data, 'to_csv') else str(data)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=filename,
            mime="text/csv"
        )

def render_empty_state(message: str = "No data available", 
                      icon: str = "📭") -> None:
    """Render an empty state message"""
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem; color: #666;">
        <h1>{icon}</h1>
        <h3>{message}</h3>
    </div>
    """, unsafe_allow_html=True)

def render_loading_spinner(message: str = "Loading...") -> None:
    """Render a loading spinner"""
    with st.spinner(message):
        pass

def create_tabs(tab_names: List[str], icons: Optional[List[str]] = None) -> List:
    """Create tabs with optional icons"""
    if icons:
        tab_labels = [f"{icon} {name}" for icon, name in zip(icons, tab_names)]
    else:
        tab_labels = tab_names
    
    return st.tabs(tab_labels)

def render_sidebar_filters(filter_config: Dict[str, Dict]) -> Dict:
    """Render sidebar filters based on configuration"""
    filters = {}
    
    st.sidebar.header("🔍 Filters")
    
    for field, config in filter_config.items():
        if config['type'] == 'select':
            value = st.sidebar.selectbox(
                config['label'],
                options=config['options'],
                format_func=config.get('format_func', lambda x: x)
            )
            if value != config.get('default'):
                filters[field] = value
                
        elif config['type'] == 'multiselect':
            value = st.sidebar.multiselect(
                config['label'],
                options=config['options'],
                default=config.get('default', [])
            )
            if value:
                filters[field] = value
                
        elif config['type'] == 'date_range':
            col1, col2 = st.sidebar.columns(2)
            with col1:
                start_date = st.date_input(
                    config['label'] + " From",
                    value=config.get('default_start')
                )
            with col2:
                end_date = st.date_input(
                    config['label'] + " To",
                    value=config.get('default_end')
                )
            filters[field] = {'start': start_date, 'end': end_date}
            
        elif config['type'] == 'number_range':
            col1, col2 = st.sidebar.columns(2)
            with col1:
                min_val = st.number_input(
                    config['label'] + " Min",
                    value=config.get('default_min', 0)
                )
            with col2:
                max_val = st.number_input(
                    config['label'] + " Max",
                    value=config.get('default_max', 1000000)
                )
            filters[field] = {'min': min_val, 'max': max_val}
    
    return filters