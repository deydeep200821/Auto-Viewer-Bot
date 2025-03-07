import asyncio
import random
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest, ImportChatInviteRequest
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple
import time

class ChannelViewer:
    def __init__(self, session_manager, proxy_manager, logger):
        self.session_manager = session_manager
        self.proxy_manager = proxy_manager
        self.logger = logger
        self.channels: Set[int] = set()
        self.groups: Set[int] = set()
        self.view_counts: Dict[str, Dict[str, int]] = {}
        self.channel_last_view: Dict[int, datetime] = {}
        self.group_last_view: Dict[int, datetime] = {}
        self.min_view_delay = 9  # seconds
        self.max_view_delay = 15  # seconds
        self.channel_cooldown = 300  # 5 minutes cooldown between views for same channel
        self.max_concurrent_views = 20
        self.view_semaphore = asyncio.Semaphore(self.max_concurrent_views)

    async def join_channel(self, username: str, client: TelegramClient, is_group: bool = False):
        """Join a channel or group using the provided client"""
        try:
            self.logger.info(f"Attempting to join {'group' if is_group else 'channel'}: {username}")
            self.logger.debug(f"Using parameters - username: {username}, is_group: {is_group}")

            # Handle invite links for groups
            if is_group and username.startswith('joinchat/'):
                self.logger.info(f"Detected group invite link: {username}")
                invite_hash = username.split('/')[-1]
                self.logger.debug(f"Extracted invite hash: {invite_hash}")
                chat = await client(ImportChatInviteRequest(invite_hash))
                chat_id = chat.chats[0].id
                if is_group:
                    self.groups.add(chat_id)
                    self.logger.info(f"Added group with ID {chat_id} to tracked groups")
                else:
                    self.channels.add(chat_id)
                    self.logger.info(f"Added channel with ID {chat_id} to tracked channels")
            else:
                # Regular channel/group join
                self.logger.info(f"Joining via username: {username}")
                channel = await client(JoinChannelRequest(username))
                if is_group:
                    self.groups.add(channel.chats[0].id)
                    self.logger.info(f"Added group with ID {channel.chats[0].id} to tracked groups")
                else:
                    self.channels.add(channel.chats[0].id)
                    self.logger.info(f"Added channel with ID {channel.chats[0].id} to tracked channels")

            self.logger.info(f"Successfully joined {'group' if is_group else 'channel'}: {username}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to join {'group' if is_group else 'channel'} {username}: {str(e)}")
            self.logger.debug(f"Error details: {type(e).__name__}")
            return False

    def can_view_chat(self, chat_id: int) -> bool:
        """Check if enough time has passed to view the chat again"""
        last_view = self.channel_last_view.get(chat_id) or self.group_last_view.get(chat_id)
        if not last_view:
            return True
        return (datetime.now() - last_view).total_seconds() >= self.channel_cooldown

    async def view_message(self, client: TelegramClient, chat_id: int, message_id: int):
        """View a specific message with rate limiting"""
        try:
            async with self.view_semaphore:
                self.logger.debug(f"Attempting to view message {message_id} in chat {chat_id}")

                # Check cooldown
                if not self.can_view_chat(chat_id):
                    self.logger.debug(f"Chat {chat_id} is still in cooldown")
                    return False

                await client.get_messages(chat_id, ids=message_id)

                # Add random delay to mimic human behavior
                delay = random.uniform(self.min_view_delay, self.max_view_delay)
                self.logger.debug(f"Adding view delay of {delay:.2f} seconds")
                await asyncio.sleep(delay)

                # Update last view time
                current_time = datetime.now()
                if chat_id in self.channels:
                    self.channel_last_view[chat_id] = current_time
                else:
                    self.group_last_view[chat_id] = current_time

                self.logger.info(f"Successfully viewed message {message_id} in chat {chat_id}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to view message {message_id}: {str(e)}")
            return False

    async def rotate_session(self, chat_id: int, message_id: int):
        """Rotate through available sessions for viewing with improved error handling"""
        self.logger.info(f"Starting session rotation for message {message_id} in chat {chat_id}")

        # Check if the chat_id is in either channels or groups
        is_valid_chat = chat_id in self.channels or chat_id in self.groups
        if not is_valid_chat:
            self.logger.warning(f"Chat {chat_id} is not in tracked channels or groups")
            return False

        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                phone = await self.session_manager.get_available_session()
                if not phone:
                    self.logger.warning("No available sessions found")
                    return False

                session_string = self.session_manager.load_session(phone)
                if not session_string:
                    self.logger.warning(f"Failed to load session for {phone}")
                    retry_count += 1
                    continue

                proxy = self.proxy_manager.get_next_proxy()
                if not proxy:
                    self.logger.warning("No available proxies")
                    retry_count += 1
                    continue

                client = TelegramClient(
                    session_string,
                    self.session_manager.api_id,
                    self.session_manager.api_hash,
                    proxy=self.proxy_manager.get_proxy_dict(proxy)
                )

                try:
                    await client.connect()
                    if await client.is_user_authorized():
                        if await self.view_message(client, chat_id, message_id):
                            self.session_manager.update_session_usage(phone)
                            return True
                finally:
                    await client.disconnect()

            except Exception as e:
                self.logger.error(f"Error with session: {str(e)}")
                self.proxy_manager.mark_proxy_failure(proxy['string'])
                retry_count += 1

            await asyncio.sleep(1)  # Brief delay between retries

        self.logger.warning(f"Failed to view message {message_id} after {max_retries} attempts")
        return False

    def get_chat_stats(self) -> Dict:
        """Get statistics about channels and groups"""
        return {
            'channels': len(self.channels),
            'groups': len(self.groups),
            'total_chats': len(self.channels) + len(self.groups),
            'active_channels': sum(1 for _ in filter(self.can_view_chat, self.channels)),
            'active_groups': sum(1 for _ in filter(self.can_view_chat, self.groups))
        }