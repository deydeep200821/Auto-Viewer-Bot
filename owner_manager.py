import json
import os
from enum import Enum
from logger import Logger

class OwnerLevel(Enum):
    HEAD = 1
    OWNER = 2
    NORMAL = 3

class OwnerManager:
    def __init__(self):
        self.owners_file = "owners.json"
        self.logger = Logger()
        self.logger.info("Initializing OwnerManager")
        self.owners = self._load_owners()

    def _load_owners(self):
        """Load owners from file"""
        # Get HEAD_OWNER_ID first
        head_owner_raw = os.getenv('HEAD_OWNER_ID', '')
        self.logger.info(f"Loading HEAD_OWNER_ID from environment: {head_owner_raw}")

        if not head_owner_raw:
            raise ValueError("HEAD_OWNER_ID environment variable is required")

        # Extract first numeric ID and convert to int
        head_owner = int(''.join(filter(str.isdigit, head_owner_raw.split()[0])))
        self.logger.info(f"Using HEAD_OWNER_ID: {head_owner}")

        # Create default structure
        default_data = {
            'head': head_owner,
            'owner': [],
            'normal': []
        }

        if os.path.exists(self.owners_file):
            try:
                with open(self.owners_file, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded existing owners file: {data}")

                    # Always use the environment variable's head owner
                    data['head'] = head_owner
                    data['owner'] = data.get('owner', [])
                    data['normal'] = data.get('normal', [])

                    # Verify data types
                    if not isinstance(data['owner'], list):
                        self.logger.warning(f"Converting owner list from {type(data['owner'])} to list")
                        data['owner'] = []
                    if not isinstance(data['normal'], list):
                        self.logger.warning(f"Converting normal list from {type(data['normal'])} to list")
                        data['normal'] = []

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                self.logger.error(f"Error loading owners file: {e}")
                data = default_data
        else:
            self.logger.info("Creating new owners file with default structure")
            data = default_data

        # Save the structure
        with open(self.owners_file, 'w') as f:
            json.dump(data, f)
            self.logger.info(f"Saved owners file with data: {data}")

        return data

    def _save_owners(self):
        """Save owners to file"""
        with open(self.owners_file, 'w') as f:
            json.dump(self.owners, f)

    def add_owner(self, owner_id, level=OwnerLevel.NORMAL):
        """Add a new owner"""
        try:
            owner_id = int(owner_id)
            if level == OwnerLevel.HEAD:
                self.owners['head'] = owner_id
            elif level == OwnerLevel.OWNER:
                if owner_id not in self.owners['owner']:
                    self.owners['owner'].append(owner_id)
            else:
                if owner_id not in self.owners['normal']:
                    self.owners['normal'].append(owner_id)
            self._save_owners()
            return True
        except ValueError:
            return False

    def remove_owner(self, owner_id, level=OwnerLevel.NORMAL):
        """Remove an owner"""
        try:
            owner_id = int(owner_id)
            if level == OwnerLevel.OWNER and owner_id in self.owners['owner']:
                self.owners['owner'].remove(owner_id)
                self._save_owners()
                return True
            elif level == OwnerLevel.NORMAL and owner_id in self.owners['normal']:
                self.owners['normal'].remove(owner_id)
                self._save_owners()
                return True
            return False
        except ValueError:
            return False

    def is_owner(self, user_id):
        """Check if user is an owner"""
        try:
            user_id = int(user_id)
            return (user_id == self.owners['head'] or 
                   user_id in self.owners['owner'] or 
                   user_id in self.owners['normal'])
        except ValueError:
            return False

    def is_head_owner(self, user_id):
        """Check if user is the head owner"""
        try:
            user_id = int(user_id)
            self.logger.info(f"Checking if user {user_id} is head owner. Head owner from config: {self.owners['head']}")
            is_head = user_id == self.owners['head']
            self.logger.info(f"Head owner check result: {is_head}")
            return is_head
        except ValueError as e:
            self.logger.error(f"Error converting user_id to int: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error in is_head_owner: {e}")
            return False

    def get_head_owner_id(self):
        """Get the head owner ID"""
        return self.owners['head']

    def is_manager(self, user_id):
        """Check if user is an owner (manager level)"""
        try:
            user_id = int(user_id)
            return user_id in self.owners['owner']
        except ValueError:
            return False

    def get_owner_level(self, user_id):
        """Get owner level for a user"""
        try:
            user_id = int(user_id)
            self.logger.info(f"Checking owner level for user {user_id}")
            self.logger.info(f"Current head owner: {self.owners['head']}")

            if user_id == self.owners['head']:
                self.logger.info(f"User {user_id} is HEAD owner")
                return OwnerLevel.HEAD
            elif user_id in self.owners['owner']:
                self.logger.info(f"User {user_id} is OWNER")
                return OwnerLevel.OWNER
            elif user_id in self.owners['normal']:
                self.logger.info(f"User {user_id} is NORMAL user")
                return OwnerLevel.NORMAL

            self.logger.info(f"User {user_id} has no recognized role")
            return None
        except ValueError as e:
            self.logger.error(f"Error in get_owner_level: {e}")
            return None

    def get_command_list(self, user_id):
        """Get list of available commands based on user level"""
        level = self.get_owner_level(user_id)

        # Basic commands for all users
        commands = [
            '/start - Start the bot and check your role',
            '/help - Show available commands',
            '/ping - Check if bot is active',
            '/contact - Get owner contact information',
            '/chat - Start chatting with Gemini AI',
            '/stop - Stop chatting with Gemini AI'
        ]

        if level == OwnerLevel.HEAD:
            commands.extend([
                '\n🔸 Head Owner Commands:',
                '/add_owner <user_id> - Add new owner',
                '/remove_owner <user_id> - Remove owner',
                '/list_owners - List all owners',
                '/owner_status - Check owner status',
                '/broadcast <message> - Send message to all users'
            ])

        if level in [OwnerLevel.HEAD, OwnerLevel.OWNER]:
            commands.extend([
                '\n🔸 Owner Commands:',
                '/add_id <phone> - Add new Telegram account',
                '/add_channel <username> - Add channel for viewing',
                '/add_group <username/invite> - Add group for viewing',
                '/view_stats - View account statistics'
            ])

        return '\n'.join(commands)