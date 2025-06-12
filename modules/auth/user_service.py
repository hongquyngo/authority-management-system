# modules/auth/user_service.py
import secrets
import string
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from config.database import execute_query
from .auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

class UserService:
    """Service layer for user management"""
    
    def __init__(self):
        self.auth_service = AuthService()
    
    def get_users(self, filters: Dict = None) -> List[Dict]:
        """Get all users with optional filters"""
        try:
            query = """
            SELECT 
                u.id,
                u.username,
                u.email,
                u.role,
                u.is_active,
                u.last_login,
                u.created_date,
                u.employee_id,
                e.id as emp_id,
                CONCAT(e.first_name, ' ', e.last_name) as full_name
            FROM users u
            LEFT JOIN employees e ON u.employee_id = e.id
            WHERE u.delete_flag = 0
            """
            
            params = {}
            
            if filters:
                if filters.get('username'):
                    query += " AND u.username LIKE :username"
                    params['username'] = f"%{filters['username']}%"
                
                if filters.get('role'):
                    query += " AND u.role = :role"
                    params['role'] = filters['role']
                
                if 'is_active' in filters:
                    query += " AND u.is_active = :is_active"
                    params['is_active'] = filters['is_active']
            
            query += " ORDER BY u.username"
            
            return execute_query(query, params) or []
            
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get single user by ID"""
        try:
            query = """
            SELECT 
                u.*,
                CONCAT(e.first_name, ' ', e.last_name) as full_name
            FROM users u
            LEFT JOIN employees e ON u.employee_id = e.id
            WHERE u.id = :id AND u.delete_flag = 0
            """
            result = execute_query(query, {'id': user_id})
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_available_employees(self) -> List[Dict]:
        """Get employees not yet linked to users"""
        try:
            query = """
            SELECT 
                e.id,
                CONCAT(e.first_name, ' ', e.last_name) as full_name,
                e.email
            FROM employees e
            WHERE e.delete_flag = 0 
            AND e.status = 'ACTIVE'
            AND e.id NOT IN (
                SELECT employee_id 
                FROM users 
                WHERE employee_id IS NOT NULL 
                AND delete_flag = 0
            )
            ORDER BY e.first_name, e.last_name
            """
            return execute_query(query) or []
        except Exception as e:
            logger.error(f"Error getting available employees: {e}")
            return []
    
    def update_user(self, user_id: int, data: Dict) -> Tuple[bool, str]:
        """Update user information"""
        try:
            # Check if username already exists (for other users)
            if 'username' in data:
                check_query = """
                SELECT COUNT(*) as count 
                FROM users 
                WHERE username = :username 
                AND id != :id
                AND delete_flag = 0
                """
                result = execute_query(check_query, {
                    'username': data['username'],
                    'id': user_id
                })
                if result[0]['count'] > 0:
                    return False, "Username already exists"
            
            # Update user
            query = """
            UPDATE users
            SET email = :email,
                role = :role,
                employee_id = :employee_id,
                is_active = :is_active,
                modified_date = NOW()
            WHERE id = :id
            """
            
            params = {
                'id': user_id,
                'email': data['email'],
                'role': data['role'],
                'employee_id': data.get('employee_id'),
                'is_active': data.get('is_active', True)
            }
            
            execute_query(query, params, fetch=False)
            return True, "User updated successfully"
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False, f"Error: {str(e)}"
    
    def toggle_user_status(self, user_id: int, is_active: bool) -> Tuple[bool, str]:
        """Activate or deactivate user"""
        try:
            # Don't allow deactivating the last active admin
            if not is_active:
                check_query = """
                SELECT COUNT(*) as count
                FROM users
                WHERE role = 'admin' 
                AND is_active = 1
                AND delete_flag = 0
                AND id != :id
                """
                result = execute_query(check_query, {'id': user_id})
                if result[0]['count'] == 0:
                    return False, "Cannot deactivate the last admin user"
            
            query = """
            UPDATE users
            SET is_active = :is_active,
                modified_date = NOW()
            WHERE id = :id
            """
            
            params = {
                'id': user_id,
                'is_active': 1 if is_active else 0
            }
            
            execute_query(query, params, fetch=False)
            status = "activated" if is_active else "deactivated"
            return True, f"User {status} successfully"
            
        except Exception as e:
            logger.error(f"Error toggling user status: {e}")
            return False, f"Error: {str(e)}"
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """Soft delete user"""
        try:
            # Don't allow deleting the last admin
            check_query = """
            SELECT 
                u.role,
                (SELECT COUNT(*) FROM users WHERE role = 'admin' AND delete_flag = 0) as admin_count
            FROM users u
            WHERE u.id = :id
            """
            result = execute_query(check_query, {'id': user_id})
            
            if result:
                user = result[0]
                if user['role'] == 'admin' and user['admin_count'] <= 1:
                    return False, "Cannot delete the last admin user"
            
            query = """
            UPDATE users
            SET delete_flag = 1,
                is_active = 0,
                modified_date = NOW()
            WHERE id = :id
            """
            
            execute_query(query, {'id': user_id}, fetch=False)
            return True, "User deleted successfully"
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False, f"Error: {str(e)}"
    
    def reset_password(self, user_id: int) -> Optional[str]:
        """Reset user password to a random password"""
        try:
            # Generate random password
            length = 12
            characters = string.ascii_letters + string.digits + "!@#$%"
            new_password = ''.join(secrets.choice(characters) for _ in range(length))
            
            # Get user info
            user = self.get_user_by_id(user_id)
            if not user:
                return None
            
            # Hash new password
            pwd_hash, salt = self.auth_service.hash_password(new_password)
            
            # Update password
            query = """
            UPDATE users
            SET password_hash = :pwd_hash,
                password_salt = :salt,
                modified_date = NOW()
            WHERE id = :id
            """
            
            params = {
                'id': user_id,
                'pwd_hash': pwd_hash,
                'salt': salt
            }
            
            execute_query(query, params, fetch=False)
            
            return new_password
            
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return None
    
    def get_user_stats(self) -> Dict:
        """Get user statistics"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_users,
                SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admin_users,
                SUM(CASE WHEN role = 'manager' THEN 1 ELSE 0 END) as manager_users,
                SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as regular_users,
                SUM(CASE WHEN last_login > DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as recent_logins
            FROM users
            WHERE delete_flag = 0
            """
            
            result = execute_query(query)
            return result[0] if result else {
                'total_users': 0,
                'active_users': 0,
                'admin_users': 0,
                'manager_users': 0,
                'regular_users': 0,
                'recent_logins': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}