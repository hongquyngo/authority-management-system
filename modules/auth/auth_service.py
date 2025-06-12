# modules/auth/auth_service.py
import hashlib
import secrets
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from config.database import execute_query
import logging

logger = logging.getLogger(__name__)

class AuthService:
    """Authentication service for user login and session management"""
    
    def __init__(self):
        self.session_timeout = timedelta(hours=8)  # 8 hour session timeout
    
    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash password with salt"""
        if not salt:
            salt = secrets.token_hex(32)
        
        # Use SHA-256 for hashing
        pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return pwd_hash, salt
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        pwd_hash, _ = self.hash_password(password, salt)
        return pwd_hash == stored_hash
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """Authenticate user with username and password"""
        try:
            # Query user from database
            query = """
            SELECT 
                u.id,
                u.username,
                u.password_hash,
                u.password_salt,
                u.email,
                u.role,
                u.is_active,
                u.last_login,
                e.id as employee_id,
                CONCAT(e.first_name, ' ', e.last_name) as full_name
            FROM users u
            LEFT JOIN employees e ON u.employee_id = e.id
            WHERE u.username = :username
            AND u.delete_flag = 0
            """
            
            result = execute_query(query, {'username': username})
            
            if not result:
                return False, {"error": "User not found"}
            
            user = result[0]
            
            # Check if user is active
            if not user['is_active']:
                return False, {"error": "User account is inactive"}
            
            # Verify password
            if not self.verify_password(password, user['password_hash'], user['password_salt']):
                return False, {"error": "Invalid password"}
            
            # Update last login
            try:
                update_query = """
                UPDATE users 
                SET last_login = NOW() 
                WHERE id = :user_id
                """
                execute_query(update_query, {'user_id': user['id']}, fetch=False)
            except Exception as e:
                logger.warning(f"Could not update last_login: {e}")
            
            # Return user info
            return True, {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'employee_id': user['employee_id'],
                'full_name': user['full_name'] or user['username']
            }
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, {"error": "Authentication failed"}
    
    def create_user(self, username: str, password: str, email: str, 
                   role: str = 'user', employee_id: Optional[int] = None) -> Tuple[bool, str]:
        """Create new user account"""
        try:
            # Check if username exists
            check_query = """
            SELECT COUNT(*) as count 
            FROM users 
            WHERE username = :username 
            AND delete_flag = 0
            """
            result = execute_query(check_query, {'username': username})
            
            if result[0]['count'] > 0:
                return False, "Username already exists"
            
            # Hash password
            pwd_hash, salt = self.hash_password(password)
            
            # Insert new user
            insert_query = """
            INSERT INTO users 
            (username, password_hash, password_salt, email, role, employee_id, 
             is_active, created_date, created_by)
            VALUES (:username, :pwd_hash, :salt, :email, :role, :employee_id,
                    1, NOW(), 'system')
            """
            
            params = {
                'username': username,
                'pwd_hash': pwd_hash,
                'salt': salt,
                'email': email,
                'role': role,
                'employee_id': employee_id
            }
            
            execute_query(insert_query, params, fetch=False)
            return True, "User created successfully"
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, f"Error: {str(e)}"
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        try:
            # Get current password info
            query = """
            SELECT password_hash, password_salt
            FROM users
            WHERE id = :user_id
            AND delete_flag = 0
            """
            result = execute_query(query, {'user_id': user_id})
            
            if not result:
                return False, "User not found"
            
            # Verify old password
            if not self.verify_password(old_password, result[0]['password_hash'], result[0]['password_salt']):
                return False, "Current password is incorrect"
            
            # Hash new password
            new_hash, new_salt = self.hash_password(new_password)
            
            # Update password
            update_query = """
            UPDATE users
            SET password_hash = :pwd_hash,
                password_salt = :salt,
                modified_date = NOW()
            WHERE id = :user_id
            """
            
            params = {
                'user_id': user_id,
                'pwd_hash': new_hash,
                'salt': new_salt
            }
            
            execute_query(update_query, params, fetch=False)
            return True, "Password changed successfully"
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False, f"Error: {str(e)}"
    
    def get_user_permissions(self, role: str) -> Dict[str, bool]:
        """Get permissions based on user role"""
        permissions = {
            'admin': {
                'can_create': True,
                'can_edit': True,
                'can_delete': True,
                'can_approve': True,
                'can_view_all': True,
                'can_export': True,
                'can_manage_users': True
            },
            'manager': {
                'can_create': True,
                'can_edit': True,
                'can_delete': False,
                'can_approve': True,
                'can_view_all': True,
                'can_export': True,
                'can_manage_users': False
            },
            'user': {
                'can_create': True,
                'can_edit': True,
                'can_delete': False,
                'can_approve': False,
                'can_view_all': False,
                'can_export': False,
                'can_manage_users': False
            }
        }
        
        return permissions.get(role, permissions['user'])

