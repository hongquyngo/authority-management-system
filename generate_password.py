# generate_password.py
import hashlib

def generate_password_hash(password, salt):
    """Generate password hash"""
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return pwd_hash

# Generate hash for admin password
password = "Admin@2024#Secure"
salt = "5f7d9e3c1a8b6f4d2e9c7a5b3d1f8e6c4a2b9d7e5f3c1a8b6d4e2f9a7c5b3d1e"

hash_result = generate_password_hash(password, salt)

print(f"Password: {password}")
print(f"Salt: {salt}")
print(f"Hash: {hash_result}")

# Generate simple password for testing
simple_password = "123"
simple_salt = "123"
simple_hash = generate_password_hash(simple_password, simple_salt)

print(f"\nSimple Password: {simple_password}")
print(f"Simple Salt: {simple_salt}")
print(f"Simple Hash: {simple_hash}")

# SQL Update statements
print("\n-- SQL to update admin password to 'Admin@2024#Secure':")
print(f"UPDATE users SET password_hash = '{hash_result}', password_salt = '{salt}' WHERE username = 'admin';")

print("\n-- SQL to update admin password to '123':")
print(f"UPDATE users SET password_hash = '{simple_hash}', password_salt = '{simple_salt}' WHERE username = 'admin';")