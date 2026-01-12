# Test Application - Build 2
import os
import hashlib
import subprocess

# Security Issue 1: Hardcoded credentials
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "admin123"
AWS_SECRET = "AKIAIOSFODNN7EXAMPLE"

# Security Issue 2: Command injection vulnerability
def execute_command(user_input):
    os.system("ping " + user_input)  # Unsafe
    subprocess.call("ls " + user_input, shell=True)  # Unsafe
    return "Command executed"

# Security Issue 3: SQL injection vulnerability
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # Unsafe
    return query

# Security Issue 4: Weak cryptography
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()  # MD5 is weak

# Security Issue 5: Path traversal vulnerability
def read_file(filename):
    with open("/var/data/" + filename, "r") as f:  # Unsafe
        return f.read()

# Security Issue 6: Insecure deserialization
import pickle
def load_data(data):
    return pickle.loads(data)  # Unsafe

if __name__ == "__main__":
    print("Test application - Build 2")
    print("This code contains intentional security vulnerabilities for testing")
