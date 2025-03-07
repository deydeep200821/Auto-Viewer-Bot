import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram API credentials
    API_ID = os.getenv('TELEGRAM_API_ID')
    API_HASH = os.getenv('TELEGRAM_API_HASH')
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Gemini API credentials
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # View settings
    MIN_VIEW_DELAY = 9  # seconds
    MAX_VIEW_DELAY = 15  # seconds
    MAX_VIEWS_PER_ACCOUNT = 100  # daily limit per account
    
    # Session settings
    SESSION_ENCRYPTION_KEY = os.getenv('SESSION_ENCRYPTION_KEY')
    
    # Proxy settings
    PROXY_ROTATION_INTERVAL = 300  # seconds
    MAX_FAILED_ATTEMPTS = 3
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'bot.log'
    
    @staticmethod
    def validate():
        """Validate required environment variables"""
        required_vars = [
            'TELEGRAM_API_ID',
            'TELEGRAM_API_HASH',
            'BOT_TOKEN',
            'SESSION_ENCRYPTION_KEY'
        ]
        
        recommended_vars = [
            'GEMINI_API_KEY'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
