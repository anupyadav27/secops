"""
Demo Application - Contains intentional security issues for testing
"""
import os
import hashlib

# Security Issue 1: Hardcoded credentials
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "admin123"
SECRET_TOKEN = "my-secret-token-12345"

# Security Issue 2: Command injection vulnerability
def execute_command(user_input):
    """Execute system command - UNSAFE!"""
    os.system("ping " + user_input)
    return "Command executed"

# Security Issue 3: SQL injection vulnerability
def get_user(user_id):
    """Query database - UNSAFE!"""
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query

# Security Issue 4: Weak cryptography
def hash_password(password):
    """Hash password using MD5 - WEAK!"""
    return hashlib.md5(password.encode()).hexdigest()

# Security Issue 5: Path traversal vulnerability
def read_file(filename):
    """Read file - UNSAFE!"""
    with open("/var/data/" + filename, "r") as f:
        return f.read()

if __name__ == "__main__":
    print("Demo application started")
