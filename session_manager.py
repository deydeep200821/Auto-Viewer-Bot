import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from datetime import datetime, timedelta
import json
import asyncio
from typing import Dict, List, Optional
from utils import encrypt_data, decrypt_data
import random

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.pending_sessions = {}
        self.session_folder = "sessions"
        self.api_id = os.getenv('TELEGRAM_API_ID')
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.active_sessions: Dict[str, datetime] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        self.max_daily_views = 100
        self.connection_pool_size = 50  # Number of simultaneous connections
        self.connection_semaphore = asyncio.Semaphore(self.connection_pool_size)

        if not os.path.exists(self.session_folder):
            os.makedirs(self.session_folder)

    async def create_session(self, phone):
        """Create a new Telegram client session"""
        async with self.connection_semaphore:
            client = TelegramClient(StringSession(), self.api_id, self.api_hash)
            await client.connect()
            await client.send_code_request(phone)
            return client

    def save_session(self, phone, encrypted_session):
        """Save encrypted session data with timestamp"""
        session_file = os.path.join(self.session_folder, f"{phone}.session")
        with open(session_file, 'w') as f:
            json.dump({
                'session': encrypted_session,
                'created_at': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat(),
                'views_today': 0,
                'total_views': 0
            }, f)

    def load_session(self, phone: str) -> Optional[str]:
        """Load and decrypt session data"""
        session_file = os.path.join(self.session_folder, f"{phone}.session")
        if not os.path.exists(session_file):
            return None

        with open(session_file, 'r') as f:
            data = json.load(f)
            return decrypt_data(data['session'])

    async def get_available_session(self) -> Optional[str]:
        """Get an available session that hasn't reached daily limit"""
        sessions = self.get_all_sessions()
        random.shuffle(sessions)  # Randomize session selection

        for phone in sessions:
            if not self.session_locks.get(phone):
                self.session_locks[phone] = asyncio.Lock()

            if self.session_locks[phone].locked():
                continue

            async with self.session_locks[phone]:
                stats = self.get_session_stats(phone)
                if stats['views_today'] < self.max_daily_views:
                    self.update_session_usage(phone)
                    return phone
        return None

    def update_session_usage(self, phone: str):
        """Update session usage statistics"""
        session_file = os.path.join(self.session_folder, f"{phone}.session")
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                data = json.load(f)

            # Reset views_today if it's a new day
            last_used = datetime.fromisoformat(data['last_used'])
            if last_used.date() < datetime.now().date():
                data['views_today'] = 0

            data['views_today'] += 1
            data['total_views'] = data.get('total_views', 0) + 1
            data['last_used'] = datetime.now().isoformat()

            with open(session_file, 'w') as f:
                json.dump(data, f)

    def get_session_stats(self, phone: str) -> Dict:
        """Get detailed statistics for a session"""
        session_file = os.path.join(self.session_folder, f"{phone}.session")
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                data = json.load(f)

            # Reset views if it's a new day
            last_used = datetime.fromisoformat(data['last_used'])
            if last_used.date() < datetime.now().date():
                data['views_today'] = 0
                with open(session_file, 'w') as f:
                    json.dump(data, f)

            return {
                'views_today': data.get('views_today', 0),
                'total_views': data.get('total_views', 0),
                'last_used': data['last_used'],
                'created_at': data['created_at']
            }
        return {
            'views_today': 0,
            'total_views': 0,
            'last_used': None,
            'created_at': None
        }

    def get_all_sessions(self) -> List[str]:
        """Get list of all active sessions"""
        sessions = []
        for file in os.listdir(self.session_folder):
            if file.endswith('.session'):
                phone = file.replace('.session', '')
                sessions.append(phone)
        return sessions

    def get_viewing_stats(self) -> Dict:
        """Get comprehensive viewing statistics for all sessions"""
        stats = {}
        total_views = 0
        active_today = 0

        for phone in self.get_all_sessions():
            session_stats = self.get_session_stats(phone)
            stats[phone] = session_stats
            total_views += session_stats['total_views']
            if session_stats['views_today'] > 0:
                active_today += 1

        return {
            'sessions': stats,
            'total_sessions': len(stats),
            'total_views': total_views,
            'active_today': active_today,
            'timestamp': datetime.now().isoformat()
        }