from cryptography.fernet import Fernet
import os
import base64
from config import Config

def generate_key():
    """Generate encryption key"""
    return Fernet.generate_key()

def encrypt_data(data: str) -> str:
    """Encrypt string data"""
    if not isinstance(data, bytes):
        data = data.encode()
    
    key = base64.b64decode(Config.SESSION_ENCRYPTION_KEY)
    f = Fernet(key)
    return f.encrypt(data).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt string data"""
    if not isinstance(encrypted_data, bytes):
        encrypted_data = encrypted_data.encode()
    
    key = base64.b64decode(Config.SESSION_ENCRYPTION_KEY)
    f = Fernet(key)
    return f.decrypt(encrypted_data).decode()

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    import re
    pattern = r'^\+\d{1,3}\d{10}$'
    return bool(re.match(pattern, phone))

def format_time_delta(seconds: int) -> str:
    """Format seconds into human readable time"""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
