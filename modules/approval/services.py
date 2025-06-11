# modules/approval/services.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import text
from config.database import execute_query
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class ApprovalAuthorityService:
    """Service layer for approval authorities"""
    
    def get_approval_types(self) -> List[Dict]:
        """Get all active approval types"""
        query = """
        SELECT id, code, name, description
        FROM approval_types
        WHERE is_active = 1 AND delete_flag = 0
        ORDER BY name
        """
        return execute_query(query)
    
    def get_companies(self) -> List[Dict]:
        """Get all active companies"""
        query = """
        SELECT id, company_code, english_name
        FROM companies
        WHERE delete_flag = 0
        ORDER BY english_name
        """
        return execute_query(query)
    
    def get_employees(self) -> List[Dict]:
        """Get all active employees"""
        query = """
        SELECT 
            id, 
            CONCAT(first_name, ' ', last_name) as full_name, 
            email,
            CONCAT(first_name, ' ', last_name, ' (', email, ')') as display_name
        FROM employees
        WHERE delete_flag = 0 AND status = 'ACTIVE'
        ORDER BY first_name, last_name
        """
        return execute_query(query)
    
    def get_authorities(self, filters: Dict = None) -> List[Dict]:
        """Get approval authorities with optional filters"""
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
        
        params = {}
        conditions = []
        
        if filters:
            if filters.get('employee_id'):
                conditions.append("aa.employee_id = :employee_id")
                params['employee_id'] = filters['employee_id']
            
            if filters.get('approval_type_id'):
                conditions.append("aa.approval_type_id = :approval_type_id")
                params['approval_type_id'] = filters['approval_type_id']
            
            if filters.get('company_id'):
                conditions.append("(aa.company_id = :company_id OR aa.company_id IS NULL)")
                params['company_id'] = filters['company_id']
            
            if filters.get('status'):
                if filters['status'] == 'Active':
                    conditions.append("aa.is_active = 1 AND (aa.valid_to IS NULL OR aa.valid_to >= CURDATE())")
                elif filters['status'] == 'Inactive':
                    conditions.append("aa.is_active = 0")
                elif filters['status'] == 'Expired':
                    conditions.append("aa.valid_to < CURDATE()")
                elif filters['status'] == 'Expiring Soon':
                    conditions.append("aa.valid_to BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)")
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " ORDER BY e.first_name, e.last_name, at.name"
        
        return execute_query(query, params)
    
    def get_authority_by_id(self, authority_id: int) -> Optional[Dict]:
        """Get single authority by ID"""
        query = """
        SELECT 
            aa.*,
            CONCAT(e.first_name, ' ', e.last_name) as employee_name,
            at.name as approval_type_name
        FROM approval_authorities aa
        JOIN employees e ON aa.employee_id = e.id
        JOIN approval_types at ON aa.approval_type_id = at.id
        WHERE aa.id = :id AND aa.delete_flag = 0
        """
        result = execute_query(query, {'id': authority_id})
        return result[0] if result else None
    
    def validate_authority(self, data: Dict, authority_id: Optional[int] = None) -> List[str]:
        """Validate authority data before saving"""
        errors = []
        
        # Check required fields
        if not data.get('employee_id'):
            errors.append("Employee is required")
        
        if not data.get('approval_type_id'):
            errors.append("Approval type is required")
        
        if not data.get('valid_from'):
            errors.append("Valid from date is required")
        
        # Validate dates
        if data.get('valid_to') and data.get('valid_from'):
            if data['valid_to'] < data['valid_from']:
                errors.append("Valid to date must be after valid from date")
        
        # Check for duplicates
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
            'employee_id': data.get('employee_id'),
            'approval_type_id': data.get('approval_type_id'),
            'company_id': data.get('company_id')
        }
        
        # Exclude current record if updating
        if authority_id:
            duplicate_query += " AND id != :id"
            params['id'] = authority_id
        
        result = execute_query(duplicate_query, params)
        if result and result[0]['count'] > 0:
            errors.append("This employee already has an active authority for this approval type and company")
        
        # Validate amount for PO approvals
        if data.get('approval_type_code') == 'PO_SUGGESTION':
            if not data.get('max_amount') or data['max_amount'] <= 0:
                errors.append("Maximum amount must be specified for PO approvals")
        
        return errors
    
    def add_authority(self, data: Dict) -> Tuple[bool, str]:
        """Add new approval authority"""
        try:
            # Validate first
            errors = self.validate_authority(data)
            if errors:
                return False, "\n".join(errors)
            
            query = """
            INSERT INTO approval_authorities 
            (employee_id, approval_type_id, company_id, valid_from, valid_to, 
             max_amount, notes, created_by, created_date, is_active, delete_flag)
            VALUES (:employee_id, :approval_type_id, :company_id, :valid_from, :valid_to,
                    :max_amount, :notes, :created_by, NOW(), 1, 0)
            """
            
            params = {
                'employee_id': data['employee_id'],
                'approval_type_id': data['approval_type_id'],
                'company_id': data.get('company_id'),
                'valid_from': data['valid_from'],
                'valid_to': data.get('valid_to'),
                'max_amount': data.get('max_amount'),
                'notes': data.get('notes', ''),
                'created_by': st.session_state.get('username', 'system')
            }
            
            execute_query(query, params, fetch=False)
            return True, "Authority added successfully"
            
        except Exception as e:
            logger.error(f"Error adding authority: {e}")
            return False, f"Error adding authority: {str(e)}"
    
    def update_authority(self, authority_id: int, data: Dict) -> Tuple[bool, str]:
        """Update existing approval authority"""
        try:
            # Validate first
            errors = self.validate_authority(data, authority_id)
            if errors:
                return False, "\n".join(errors)
            
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
            WHERE id = :id
            """
            
            params = {
                'id': authority_id,
                'employee_id': data['employee_id'],
                'approval_type_id': data['approval_type_id'],
                'company_id': data.get('company_id'),
                'valid_from': data['valid_from'],
                'valid_to': data.get('valid_to'),
                'max_amount': data.get('max_amount'),
                'notes': data.get('notes', ''),
                'modified_by': st.session_state.get('username', 'system')
            }
            
            execute_query(query, params, fetch=False)
            return True, "Authority updated successfully"
            
        except Exception as e:
            logger.error(f"Error updating authority: {e}")
            return False, f"Error updating authority: {str(e)}"
    
    def toggle_authority_status(self, authority_id: int, is_active: bool) -> Tuple[bool, str]:
        """Activate or deactivate an authority"""
        try:
            query = """
            UPDATE approval_authorities 
            SET is_active = :is_active,
                modified_by = :modified_by,
                modified_date = NOW()
            WHERE id = :id
            """
            
            params = {
                'id': authority_id,
                'is_active': 1 if is_active else 0,
                'modified_by': st.session_state.get('username', 'system')
            }
            
            execute_query(query, params, fetch=False)
            status = "activated" if is_active else "deactivated"
            return True, f"Authority {status} successfully"
            
        except Exception as e:
            logger.error(f"Error toggling authority status: {e}")
            return False, f"Error changing status: {str(e)}"
    
    def delete_authority(self, authority_id: int) -> Tuple[bool, str]:
        """Soft delete an authority"""
        try:
            query = """
            UPDATE approval_authorities 
            SET delete_flag = 1,
                modified_by = :modified_by,
                modified_date = NOW()
            WHERE id = :id
            """
            
            params = {
                'id': authority_id,
                'modified_by': st.session_state.get('username', 'system')
            }
            
            execute_query(query, params, fetch=False)
            return True, "Authority deleted successfully"
            
        except Exception as e:
            logger.error(f"Error deleting authority: {e}")
            return False, f"Error deleting authority: {str(e)}"
    
    def get_authority_history(self, authority_id: int) -> List[Dict]:
        """Get modification history for an authority"""
        # This would require an audit table in real implementation
        # For now, return empty list
        return []
    
    def bulk_import_authorities(self, data: List[Dict]) -> Tuple[int, List[str]]:
        """Import multiple authorities from Excel/CSV"""
        success_count = 0
        errors = []
        
        for idx, row in enumerate(data):
            try:
                # Validate and add each row
                result, message = self.add_authority(row)
                if result:
                    success_count += 1
                else:
                    errors.append(f"Row {idx + 2}: {message}")
            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
        
        return success_count, errors