import requests
import json
import time
from typing import Dict, Optional, List
import random
from datetime import datetime, timedelta

class ProxyManager:
    def __init__(self):
        self.proxies = {}
        self.current_proxy = None
        self.last_rotation = 0
        self.proxy_file = "proxies.json"
        self.max_failures = 3
        self.failure_timeout = 1800  # 30 minutes timeout for failed proxies
        self.min_proxy_speed = 1.0  # minimum speed in MB/s
        self.connection_timeout = 10  # seconds
        self._load_proxies()

    def _load_proxies(self):
        """Load proxies from file"""
        try:
            with open(self.proxy_file, 'r') as f:
                data = json.load(f)
                # Convert stored timestamps to datetime objects
                for proxy in data.values():
                    if 'last_check' in proxy:
                        proxy['last_check'] = datetime.fromisoformat(proxy['last_check'])
                    if 'failure_time' in proxy:
                        proxy['failure_time'] = datetime.fromisoformat(proxy['failure_time'])
                self.proxies = data
        except FileNotFoundError:
            self.proxies = {}

    def _save_proxies(self):
        """Save proxies to file"""
        # Convert datetime objects to ISO format for JSON serialization
        data = {}
        for proxy_id, proxy in self.proxies.items():
            proxy_data = proxy.copy()
            if 'last_check' in proxy_data:
                proxy_data['last_check'] = proxy_data['last_check'].isoformat()
            if 'failure_time' in proxy_data:
                proxy_data['failure_time'] = proxy_data['failure_time'].isoformat()
            data[proxy_id] = proxy_data

        with open(self.proxy_file, 'w') as f:
            json.dump(data, f)

    def add_proxy(self, proxy_string: str, proxy_type: str = 'socks5'):
        """Add a new proxy to the pool"""
        proxy_id = str(len(self.proxies) + 1)
        self.proxies[proxy_id] = {
            'string': proxy_string,
            'type': proxy_type,
            'last_used': 0,
            'failures': 0,
            'success_count': 0,
            'last_check': datetime.now(),
            'speed': None,
            'failure_time': None
        }
        self._save_proxies()

    def remove_proxy(self, proxy_id: str):
        """Remove a proxy from the pool"""
        if proxy_id in self.proxies:
            del self.proxies[proxy_id]
            self._save_proxies()

    def test_proxy(self, proxy_data: Dict) -> bool:
        """Test proxy connection and speed"""
        try:
            proxy_dict = self.get_proxy_dict(proxy_data)
            start_time = time.time()
            response = requests.get(
                'https://www.google.com',
                proxies=proxy_dict,
                timeout=self.connection_timeout
            )
            end_time = time.time()

            if response.status_code == 200:
                # Calculate speed in MB/s
                speed = len(response.content) / (1024 * 1024 * (end_time - start_time))
                proxy_data['speed'] = speed
                proxy_data['last_check'] = datetime.now()
                return speed >= self.min_proxy_speed
        except:
            return False
        return False

    def get_next_proxy(self) -> Optional[Dict]:
        """Get the next available proxy using improved selection"""
        if not self.proxies:
            return None

        # Filter out recently failed proxies
        current_time = datetime.now()
        available_proxies = {
            k: v for k, v in self.proxies.items()
            if v['failures'] < self.max_failures and
            (not v['failure_time'] or 
             (current_time - v['failure_time']).total_seconds() > self.failure_timeout)
        }

        if not available_proxies:
            return None

        # Sort proxies by failures (ascending) and success_count (descending)
        proxy_list = list(available_proxies.items())
        random.shuffle(proxy_list)  # Add randomization
        proxy_list.sort(key=lambda x: (x[1]['failures'], -x[1]['success_count']))

        # Take the best proxy
        selected_proxy = proxy_list[0][1]
        selected_proxy['last_used'] = time.time()
        self._save_proxies()

        # Test the proxy before returning
        if self.test_proxy(selected_proxy):
            selected_proxy['success_count'] += 1
            return selected_proxy

        # If test failed, mark as failure and try next best proxy
        self.mark_proxy_failure(selected_proxy['string'])
        return self.get_next_proxy()

    def mark_proxy_failure(self, proxy_string: str):
        """Mark a proxy as failed with timeout"""
        for proxy in self.proxies.values():
            if proxy['string'] == proxy_string:
                proxy['failures'] += 1
                proxy['failure_time'] = datetime.now()
                if proxy['failures'] >= self.max_failures:
                    proxy['last_check'] = datetime.now()
                self._save_proxies()
                break

    def mark_proxy_success(self, proxy_string: str):
        """Mark a proxy as successful"""
        for proxy in self.proxies.values():
            if proxy['string'] == proxy_string:
                proxy['failures'] = max(0, proxy['failures'] - 1)  # Decrease failure count
                proxy['success_count'] += 1
                proxy['failure_time'] = None
                self._save_proxies()
                break

    def get_proxy_dict(self, proxy_data: Dict) -> Dict:
        """Convert proxy data to requests format"""
        return {
            'http': f"{proxy_data['type']}://{proxy_data['string']}",
            'https': f"{proxy_data['type']}://{proxy_data['string']}"
        }

    def get_proxy_stats(self) -> Dict:
        """Get statistics about proxy usage"""
        total_proxies = len(self.proxies)
        available_proxies = sum(1 for p in self.proxies.values() if p['failures'] < self.max_failures)
        failed_proxies = total_proxies - available_proxies

        return {
            'total_proxies': total_proxies,
            'available_proxies': available_proxies,
            'failed_proxies': failed_proxies,
            'success_rate': sum(p['success_count'] for p in self.proxies.values()),
            'timestamp': datetime.now().isoformat()
        }