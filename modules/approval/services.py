# modules/approval/services.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text
from config.database import execute_query
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class ApprovalAuthorityService:
    """Service layer for approval authorities"""
    
    def get_approval_types(self) -> List[Dict]:
        """Get all active approval types"""
        try:
            query = """
            SELECT id, code, name, description
            FROM approval_types
            WHERE is_active = 1 AND delete_flag = 0
            ORDER BY name
            """
            return execute_query(query) or []
        except Exception as e:
            logger.error(f"Error getting approval types: {e}")
            return []
    
    def get_companies(self) -> List[Dict]:
        """Get all active companies"""
        try:
            query = """
            SELECT id, company_code, english_name
            FROM companies
            WHERE delete_flag = 0
            ORDER BY english_name
            """
            return execute_query(query) or []
        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            return []
    
    def get_employees(self) -> List[Dict]:
        """Get all active employees"""
        try:
            query = """
            SELECT 
                id, 
                CONCAT(first_name, ' ', last_name) as full_name, 
                email
            FROM employees
            WHERE delete_flag = 0 AND status = 'ACTIVE'
            ORDER BY first_name, last_name
            """
            return execute_query(query) or []
        except Exception as e:
            logger.error(f"Error getting employees: {e}")
            return []
    
    def get_authorities(self, filters: Dict = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get approval authorities with optional filters and pagination"""
        try:
            query = """
            SELECT 
                aa.id,
                aa.employee_id,
                CONCAT(e.first_name, ' ', e.last_name) as employee_name,
                e.email,
                aa.approval_type_id,
                at.code as approval_type_code,
                at.name as approval_type_name,
                aa.company_id,
                c.company_code,
                c.english_name as company_name,
                aa.is_active,
                aa.valid_from,
                aa.valid_to,
                aa.max_amount,
                aa.notes,
                aa.created_date,
                aa.created_by,
                CASE 
                    WHEN aa.is_active = 0 THEN 'Inactive'
                    WHEN aa.valid_to IS NOT NULL AND aa.valid_to < CURDATE() THEN 'Expired'
                    WHEN aa.valid_to IS NOT NULL AND aa.valid_to <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN 'Expiring Soon'
                    ELSE 'Active'
                END as status
            FROM approval_authorities aa
            JOIN employees e ON aa.employee_id = e.id
            JOIN approval_types at ON aa.approval_type_id = at.id
            LEFT JOIN companies c ON aa.company_id = c.id
            WHERE aa.delete_flag = 0
            """
            
            params = {'limit': limit, 'offset': offset}
            
            # Apply filters safely
            if filters:
                if filters.get('employee_id'):
                    query += " AND aa.employee_id = :employee_id"
                    params['employee_id'] = int(filters['employee_id'])
                
                if filters.get('approval_type_id'):
                    query += " AND aa.approval_type_id = :approval_type_id"
                    params['approval_type_id'] = int(filters['approval_type_id'])
                
                if filters.get('company_id'):
                    query += " AND (aa.company_id = :company_id OR aa.company_id IS NULL)"
                    params['company_id'] = int(filters['company_id'])
                
                if filters.get('status'):
                    if filters['status'] == 'Active':
                        query += " AND aa.is_active = 1 AND (aa.valid_to IS NULL OR aa.valid_to >= CURDATE())"
                    elif filters['status'] == 'Inactive':
                        query += " AND aa.is_active = 0"
                    elif filters['status'] == 'Expired':
                        query += " AND aa.valid_to < CURDATE()"
                    elif filters['status'] == 'Expiring Soon':
                        query += " AND aa.valid_to BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)"
            
            query += " ORDER BY e.first_name, e.last_name, at.name LIMIT :limit OFFSET :offset"
            
            return execute_query(query, params) or []
        except Exception as e:
            logger.error(f"Error getting authorities: {e}")
            return []
    
    def get_authority_by_id(self, authority_id: int) -> Optional[Dict]:
        """Get single authority by ID"""
        try:
            query = """
            SELECT 
                aa.*,
                CONCAT(e.first_name, ' ', e.last_name) as employee_name,
                at.name as approval_type_name,
                at.code as approval_type_code
            FROM approval_authorities aa
            JOIN employees e ON aa.employee_id = e.id
            JOIN approval_types at ON aa.approval_type_id = at.id
            WHERE aa.id = :id AND aa.delete_flag = 0
            """
            result = execute_query(query, {'id': int(authority_id)})
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting authority by id: {e}")
            return None
    
    def validate_authority(self, data: Dict, authority_id: Optional[int] = None) -> List[str]:
        """Validate authority data before saving"""
        errors = []
        
        # Required fields
        if not data.get('employee_id'):
            errors.append("Employee is required")
        
        if not data.get('approval_type_id'):
            errors.append("Approval type is required")
        
        if not data.get('valid_from'):
            errors.append("Valid from date is required")
        
        # Validate IDs exist
        if data.get('employee_id'):
            emp_query = "SELECT COUNT(*) as count FROM employees WHERE id = :id AND delete_flag = 0"
            result = execute_query(emp_query, {'id': int(data['employee_id'])})
            if not result or result[0]['count'] == 0:
                errors.append("Selected employee does not exist")
        
        if data.get('approval_type_id'):
            type_query = "SELECT COUNT(*) as count FROM approval_types WHERE id = :id AND delete_flag = 0"
            result = execute_query(type_query, {'id': int(data['approval_type_id'])})
            if not result or result[0]['count'] == 0:
                errors.append("Selected approval type does not exist")
        
        # Date validation
        if data.get('valid_from'):
            # Check if date is not too far in the past (more than 1 year)
            one_year_ago = datetime.now().date() - timedelta(days=365)
            if data['valid_from'] < one_year_ago:
                errors.append("Valid from date cannot be more than 1 year in the past")
        
        if data.get('valid_to') and data.get('valid_from'):
            if data['valid_to'] < data['valid_from']:
                errors.append("Valid to date must be after valid from date")
            
            # Check if date range is not too long (more than 5 years)
            if (data['valid_to'] - data['valid_from']).days > 1825:  # 5 years
                errors.append("Date range cannot exceed 5 years")
        
        # Amount validation for specific types
        if data.get('approval_type_code') in ['PO_SUGGESTION', 'PO_CANCELLATION', 'OC_CANCELLATION', 'OC_RETURN']:
            if not data.get('max_amount') or float(data['max_amount']) <= 0:
                errors.append("Maximum amount must be specified and greater than 0")
            elif float(data['max_amount']) > 999999999:
                errors.append("Maximum amount is too large")
        
        # Check for duplicates
        if data.get('employee_id') and data.get('approval_type_id'):
            duplicate_query = """
            SELECT COUNT(*) as count
            FROM approval_authorities
            WHERE employee_id = :employee_id
            AND approval_type_id = :approval_type_id
            AND (company_id = :company_id OR (company_id IS NULL AND :company_id IS NULL))
            AND delete_flag = 0
            AND is_active = 1
            AND (valid_to IS NULL OR valid_to >= CURDATE())
            """
            
            params = {
                'employee_id': int(data['employee_id']),
                'approval_type_id': int(data['approval_type_id']),
                'company_id': int(data['company_id']) if data.get('company_id') else None
            }
            
            if authority_id:
                duplicate_query += " AND id != :id"
                params['id'] = int(authority_id)
            
            result = execute_query(duplicate_query, params)
            if result and result[0]['count'] > 0:
                errors.append("Active authority already exists for this combination")
        
        return errors
    
    def add_authority(self, data: Dict) -> Tuple[bool, str]:
        """Add new approval authority with transaction"""
        try:
            # Get approval type code
            type_query = "SELECT code FROM approval_types WHERE id = :id"
            type_result = execute_query(type_query, {'id': int(data['approval_type_id'])})
            if type_result:
                data['approval_type_code'] = type_result[0]['code']
            
            # Validate
            errors = self.validate_authority(data)
            if errors:
                return False, "; ".join(errors)
            
            query = """
            INSERT INTO approval_authorities 
            (employee_id, approval_type_id, company_id, valid_from, valid_to, 
             max_amount, notes, created_by, created_date, is_active, delete_flag)
            VALUES (:employee_id, :approval_type_id, :company_id, :valid_from, :valid_to,
                    :max_amount, :notes, :created_by, NOW(), 1, 0)
            """
            
            params = {
                'employee_id': int(data['employee_id']),
                'approval_type_id': int(data['approval_type_id']),
                'company_id': int(data['company_id']) if data.get('company_id') else None,
                'valid_from': data['valid_from'],
                'valid_to': data.get('valid_to'),
                'max_amount': float(data['max_amount']) if data.get('max_amount') else None,
                'notes': str(data.get('notes', ''))[:500],  # Limit notes length
                'created_by': st.session_state.get('username', 'system')
            }
            
            execute_query(query, params, fetch=False)
            return True, "Authority added successfully"
            
        except Exception as e:
            logger.error(f"Error adding authority: {e}")
            return False, f"Error: {str(e)}"
    
    def update_authority(self, authority_id: int, data: Dict) -> Tuple[bool, str]:
        """Update existing approval authority with transaction"""
        try:
            # Get approval type code
            type_query = "SELECT code FROM approval_types WHERE id = :id"
            type_result = execute_query(type_query, {'id': int(data['approval_type_id'])})
            if type_result:
                data['approval_type_code'] = type_result[0]['code']
            
            # Validate
            errors = self.validate_authority(data, authority_id)
            if errors:
                return False, "; ".join(errors)
            
            query = """
            UPDATE approval_authorities 
            SET employee_id = :employee_id,
                approval_type_id = :approval_type_id,
                company_id = :company_id,
                valid_from = :valid_from,
                valid_to = :valid_to,
                max_amount = :max_amount,
                notes = :notes,
                modified_by = :modified_by,
                modified_date = NOW()
            WHERE id = :id AND delete_flag = 0
            """
            
            params = {
                'id': int(authority_id),
                'employee_id': int(data['employee_id']),
                'approval_type_id': int(data['approval_type_id']),
                'company_id': int(data['company_id']) if data.get('company_id') else None,
                'valid_from': data['valid_from'],
                'valid_to': data.get('valid_to'),
                'max_amount': float(data['max_amount']) if data.get('max_amount') else None,
                'notes': str(data.get('notes', ''))[:500],  # Limit notes length
                'modified_by': st.session_state.get('username', 'system')
            }
            
            execute_query(query, params, fetch=False)
            return True, "Authority updated successfully"
            
        except Exception as e:
            logger.error(f"Error updating authority: {e}")
            return False, f"Error: {str(e)}"
    
    def toggle_authority_status(self, authority_id: int, is_active: bool) -> Tuple[bool, str]:
        """Activate or deactivate an authority"""
        try:
            query = """
            UPDATE approval_authorities 
            SET is_active = :is_active,
                modified_by = :modified_by,
                modified_date = NOW()
            WHERE id = :id AND delete_flag = 0
            """
            
            params = {
                'id': int(authority_id),
                'is_active': 1 if is_active else 0,
                'modified_by': st.session_state.get('username', 'system')
            }
            
            execute_query(query, params, fetch=False)
            status = "activated" if is_active else "deactivated"
            return True, f"Authority {status} successfully"
            
        except Exception as e:
            logger.error(f"Error toggling authority status: {e}")
            return False, f"Error: {str(e)}"
    
    def delete_authority(self, authority_id: int) -> Tuple[bool, str]:
        """Soft delete an authority"""
        try:
            query = """
            UPDATE approval_authorities 
            SET delete_flag = 1,
                is_active = 0,
                modified_by = :modified_by,
                modified_date = NOW()
            WHERE id = :id
            """
            
            params = {
                'id': int(authority_id),
                'modified_by': st.session_state.get('username', 'system')
            }
            
            execute_query(query, params, fetch=False)
            return True, "Authority deleted successfully"
            
        except Exception as e:
            logger.error(f"Error deleting authority: {e}")
            return False, f"Error: {str(e)}"