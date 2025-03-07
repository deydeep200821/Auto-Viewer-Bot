import logging
import os
from datetime import datetime
from config import Config

class Logger:
    def __init__(self):
        self.logger = logging.getLogger('TelegramViewBot')
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # File handler
        file_handler = logging.FileHandler(Config.LOG_FILE)
        file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def info(self, message):
        self.logger.info(message)
        
    def error(self, message):
        self.logger.error(message)
        
    def warning(self, message):
        self.logger.warning(message)
        
    def debug(self, message):
        self.logger.debug(message)
        
    def log_view(self, account, channel, message_id):
        """Log view activity"""
        self.info(f"View: Account {account} viewed message {message_id} in {channel}")
        
    def log_join(self, account, channel):
        """Log channel join activity"""
        self.info(f"Join: Account {account} joined channel {channel}")
        
    def log_session(self, account, action):
        """Log session related activity"""
        self.info(f"Session: Account {account} - {action}")
        
    def log_owner_action(self, owner_id, action):
        """Log owner actions"""
        self.info(f"Owner {owner_id}: {action}")
