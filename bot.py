
import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from dotenv import load_dotenv
import random
from datetime import datetime
import google.generativeai as genai
import pytz

from session_manager import SessionManager
from owner_manager import OwnerManager, OwnerLevel
from proxy_manager import ProxyManager
from channel_viewer import ChannelViewer
from config import Config
from logger import Logger
from utils import encrypt_data, decrypt_data

load_dotenv()

class TelegramViewBot:
    def __init__(self):
        # Initialize logger first to ensure it's available for all subsequent operations
        self.logger = Logger()
        self.logger.info("Initializing TelegramViewBot...")
        
        # Initialize chat storage
        self.chat_sessions = {}  # Store chat sessions for users
        self.all_users = set()  # Store all user IDs for broadcasting
        
        # Initialize Gemini with the valid API key
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyD_B8v-rw__vR-BKsGm1-riHqyhBa9b4Vc')
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Use try-except to handle Gemini API initialization errors
        try:
            generation_config = {
                "temperature": 0.9,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 2048,
            }
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]

            self.model = genai.GenerativeModel(
                model_name='gemini-pro',
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            self.vision_model = genai.GenerativeModel(
                model_name='gemini-pro-vision',
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            self.gemini_available = True
            self.logger.info("Gemini models initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini models: {str(e)}")
            self.gemini_available = False

        self.api_id = os.getenv('TELEGRAM_API_ID')
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.bot_token = os.getenv('BOT_TOKEN')

        if not all([self.api_id, self.api_hash, self.bot_token]):
            self.logger.error("Missing required environment variables!")
            raise ValueError("Missing required environment variables!")

        self.logger.info("Loading components...")
        self.session_manager = SessionManager()
        self.owner_manager = OwnerManager()
        self.proxy_manager = ProxyManager()
        self.channel_viewer = ChannelViewer(self.session_manager, self.proxy_manager, self.logger)
        self.life_quotes = [
            "Life is what happens while you're busy making other plans. - John Lennon",
            "The purpose of our lives is to be happy. - Dalai Lama",
            "Life is either a daring adventure or nothing at all. - Helen Keller",
            "Live in the sunshine, swim the sea, drink the wild air. - Ralph Waldo Emerson",
            "Life is really simple, but we insist on making it complicated. - Confucius",

            "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन। - Do your duty without expecting the fruits of your actions.",
            "जो बीत गयी सो बात गयी। - What's gone is gone, focus on the present.",
            "योग: कर्मसु कौशलम्। - Yoga is excellence in action.",
            "मन एव मनुष्याणां कारणं बन्धमोक्षयो:। - The mind is the cause of bondage and liberation.",
            "श्रेयान्स्वधर्मो विगुण: परधर्मात्स्वनुष्ठितात्। - Better is one's own dharma than the dharma of another.",

            "राधा कृष्ण प्रेम की गागर, प्रेम रस से भरपूर है।",
            "राधे राधे जपो चलो मन, राधे कृष्ण रटो।",
            "कृष्ण प्रेम में रंग जाओ, राधा नाम में खो जाओ।",
            "राधा माधव की जोड़ी, जैसी और न कोई।",
            "राधा रानी की कृपा से, कृष्ण भक्ति मिल जाए।",

            "जहाँ भक्ति, वहाँ शक्ति। - Where there is devotion, there is power.",
            "सत्य की राह पर चलो, मंजिल अपने आप मिल जाएगी।",
            "धर्म की राह पर चलना ही जीवन का सार है।",
            "कर्म करो, फल की चिंता मत करो।",
            "आत्मा परमात्मा का अंश है।",

            "प्रेम वह भाव है जो बिना कहे समझा जाता है।",
            "सच्चा प्यार समर्पण है, स्वार्थ नहीं।",
            "प्रेम में जाति, धर्म, भाषा की दीवारें नहीं होतीं।",
            "प्यार करो तो दिल से करो, दिखावा मत करो।",
            "प्रेम वह है जो बिना मांगे मिल जाए।",

            "जब तक जीवन है, तब तक सीखना जारी रखो।",
            "क्रोध से बुद्धि नष्ट होती है।",
            "सबसे बड़ा धर्म है दया और करुणा।",
            "मनुष्य अपने विचारों से ही अपना भविष्य बनाता है।",
            "ज्ञान से बड़ा कोई धन नहीं।",

            "जो भी होता है, अच्छे के लिए होता है।",
            "अहंकार मनुष्य का सबसे बड़ा शत्रु है।",
            "कर्म करते रहो, फल की चिंता मत करो।",
            "सत्य की जीत होती है, असत्य की नहीं।",
            "धैर्य रखो, सब ठीक हो जाएगा।",

            "सबक सीखो और आगे बढ़ो।",
            "गलतियों से सीखो, लेकिन उनमें मत डूबो।",
            "जीवन एक पाठशाला है, हर दिन कुछ नया सिखाती है।",
            "समय सबसे बड़ा शिक्षक है।",
            "परिवर्तन ही जीवन का नियम है।",

            "आत्मज्ञान सबसे बड़ा ज्ञान है।",
            "सेवा ही जीवन का सार है।",
            "प्रेम और करुणा से बड़ा कोई धर्म नहीं।",
            "शांति के लिए मन की शुद्धि आवश्यक है।",
            "सत्य, अहिंसा और प्रेम जीवन के मूल मंत्र हैं।",

            "श्रद्धा ही सफलता की कुंजी है।",
            "प्रेम और कर्तव्य में संतुलन आवश्यक है।",
            "धैर्य से हर मुश्किल का हल मिलता है।",
            "विश्वास रखो, सब ठीक होगा।",
            "जीवन में संघर्ष ही विकास का मार्ग है।",

            "राधा की भक्ति में कृष्ण का वास है।",
            "प्रेम का पथ कठिन है, पर सुंदर है।",
            "राधा कृष्ण का प्रेम अमर है।",
            "भक्ति में शक्ति है।",
            "कृष्ण की लीला अपरंपार है।",

            "निष्काम कर्म ही सच्चा कर्म है।",
            "स्थितप्रज्ञ बनो, विचलित न हो।",
            "समर्पण में ही सच्ची शांति है।",
            "कर्म ही पूजा है।",
            "आत्मविश्वास ही सफलता का मूल है।",

            "सेवा में सुख है।",
            "क्षमा वीरों का गहना है।",
            "धैर्य से सब संभव है।",
            "करुणा मानवता का गहना है।",
            "विनम्रता शक्ति का चिन्ह है।",

            "प्रेम में ही ईश्वर का वास है।",
            "सच्चा प्रेम कभी मरता नहीं।",
            "प्रेम से बड़ी कोई पूजा नहीं।",
            "प्रेम ही जीवन का सार है।",
            "जहाँ प्रेम है, वहाँ ईश्वर है।"
        ]

        try:
            self.logger.info("Starting Telegram client...")
            # Use a unique session name to avoid conflicts
            import uuid
            session_id = str(uuid.uuid4())[:8]
            self.bot = TelegramClient(f'bot_{session_id}', self.api_id, self.api_hash)
            
            # Connect with proper error handling
            self.logger.info("Connecting to Telegram...")
            self.bot.start(bot_token=self.bot_token)
            self.logger.info("Telegram client started successfully!")
        except Exception as e:
            self.logger.error(f"Failed to start Telegram client: {str(e)}")
            raise

    def get_time_based_greeting(self, hour: int, name: str) -> str:
        """Get appropriate greeting based on time of day"""
        if 6 <= hour < 12:
            return f"Good Morning, {name}"
        elif 12 <= hour < 13:
            return f"Good Noon, {name}"
        elif 13 <= hour < 17:
            return f"Good Afternoon, {name}"
        elif 17 <= hour < 19:
            return f"Good Evening, {name}"
        elif 19 <= hour < 24:
            return f"Good Night, {name}"
        else:  # 0-6
            return f"Good Midnight, {name}"


    async def start(self):
        @self.bot.on(events.NewMessage(pattern='/chat'))
        async def chat_handler(event):
            sender = await event.get_sender()
            sender_id = sender.id

            if sender_id in self.chat_sessions:
                await event.respond("You're already in chat mode! Use /stop to exit.")
                return

            if not hasattr(self, 'gemini_available') or not self.gemini_available:
                error_message = (
                    "⚠️ Gemini AI is currently unavailable.\n\n"
                    "Please make sure you have:\n"
                    "1️⃣ Added a valid GEMINI_API_KEY to your environment variables\n"
                    "2️⃣ Installed the proper Google Generative AI package\n\n"
                    "Contact the bot administrator for assistance."
                )
                await event.respond(error_message)
                return

            try:
                # Reinitialize Gemini model if needed
                if not hasattr(self, 'model') or self.model is None:
                    self.logger.info("Reinitializing Gemini model for chat")
                    generation_config = {
                        "temperature": 0.9,
                        "top_p": 1,
                        "top_k": 1,
                        "max_output_tokens": 2048,
                    }
                    safety_settings = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    ]
                    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyD_B8v-rw__vR-BKsGm1-riHqyhBa9b4Vc')
                    genai.configure(api_key=GEMINI_API_KEY)
                    self.model = genai.GenerativeModel(
                        model_name='gemini-pro',
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )
                
                self.logger.info(f"Starting chat for user {sender_id}")
                chat = self.model.start_chat(history=[])
                initial_prompt = "You are a helpful and friendly AI assistant. Always be respectful and provide accurate information. If you're unsure about something, say so."
                chat.send_message(initial_prompt)
                self.chat_sessions[sender_id] = chat
                self.logger.info(f"Chat session successfully created for user {sender_id}")

                welcome_message = (
                    "🤖 Welcome to Gemini AI Chat Mode!\n\n"
                    "You can:\n"
                    "1️⃣ Chat naturally with AI\n"
                    "2️⃣ Generate image descriptions by typing:\n"
                    "   • 'generate image [description]'\n"
                    "   • 'create image [description]'\n"
                    "   • 'make image [description]'\n\n"
                    "❌ Use /stop to exit chat mode\n\n"
                    "Try asking something! 😊"
                )
                await event.respond(welcome_message)
            except Exception as e:
                self.logger.error(f"Error starting chat: {str(e)}")
                await event.respond("Sorry, I couldn't start the chat session. Please try again later.")

        @self.bot.on(events.NewMessage(pattern='/stop'))
        async def stop_chat_handler(event):
            sender = await event.get_sender()
            sender_id = sender.id

            if sender_id in self.chat_sessions:
                del self.chat_sessions[sender_id]
                await event.respond("Chat mode deactivated. Returning to auto-view mode.\n\nUse /help to see available commands.")
            else:
                await event.respond("You're not in chat mode! Use /chat to start chatting.")

        @self.bot.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            sender = await event.get_sender()
            sender_id = sender.id
            sender_name = sender.first_name  # Get user's first name
            self.logger.info(f"Processing /start command for user {sender_id}")

            # Add user to broadcast list
            self.all_users.add(sender_id)

            # Get current Indian time
            india_tz = pytz.timezone('Asia/Kolkata')
            current_time = datetime.now(india_tz)
            time_str = current_time.strftime('%Y-%m-%d %I:%M:%S %p IST')

            # Get time-based greeting
            greeting = self.get_time_based_greeting(current_time.hour, sender_name)

            # Get user's role
            level = self.owner_manager.get_owner_level(sender_id)
            self.logger.info(f"User {sender_id} has level: {level}")

            role = "Not Authorized"
            response_text = ""

            if level == OwnerLevel.HEAD:
                role = "Head Owner"
                self.logger.info(f"User {sender_id} is Head Owner")
                response_text = (
                    f"{greeting}!\n\n"
                    f"Welcome to Telegram Auto-View Bot!\n"
                    f"Your ID: {sender_id}\n"
                    f"Your Role: {role}\n\n"
                    f"Use /help to see available commands\n"
                    f"Use /contact for owner information\n"
                    f"Use /chat to talk with Gemini AI\n\n"
                    f"🕒 Current Time: {time_str}"
                )
            elif level == OwnerLevel.OWNER:
                role = "Owner"
                self.logger.info(f"User {sender_id} is Owner")
                response_text = (
                    f"{greeting}!\n\n"
                    f"Welcome to Telegram Auto-View Bot!\n"
                    f"Your ID: {sender_id}\n"
                    f"Your Role: {role}\n\n"
                    f"Use /help to see available commands\n"
                    f"Use /contact for owner information\n"
                    f"Use /chat to talk with Gemini AI\n\n"
                    f"🕒 Current Time: {time_str}"
                )
            elif level == OwnerLevel.NORMAL:
                role = "Normal User"
                self.logger.info(f"User {sender_id} is Normal User")
                response_text = (
                    f"{greeting}!\n\n"
                    f"Welcome to Telegram Auto-View Bot!\n"
                    f"Your ID: {sender_id}\n"
                    f"Your Role: {role}\n\n"
                    f"Use /help to see available commands\n"
                    f"Use /contact for owner information\n"
                    f"Use /chat to talk with Gemini AI\n\n"
                    f"🕒 Current Time: {time_str}"
                )
            else:
                response_text = (
                    f"{greeting}!\n\n"
                    f"Welcome to Telegram Auto-View Bot!\n"
                    f"Your ID: {sender_id}\n"
                    f"Your Role: {role}\n\n"
                    f"🔥 Want to become an owner and get access to premium features?\n"
                    f"✨ Premium Plan Benefits:\n"
                    f"  • Add unlimited Telegram accounts\n"
                    f"  • Automatic views on all posts\n"
                    f"  • Smart anti-ban protection\n"
                    f"  • 24/7 automated viewing\n\n"
                    f"💎 Special Price: Only 4000 rs!\n\n"
                    f"Use /contact to get owner contact information!\n"
                    f"Use /help to see available commands\n"
                    f"Use /chat to talk with Gemini AI\n\n"
                    f"🕒 Current Time: {time_str}"
                )

            self.logger.info(f"Assigned role {role} to user {sender_id}")
            await event.respond(response_text)

        @self.bot.on(events.NewMessage(pattern='/ping'))
        async def ping_handler(event):
            self.logger.info("Received ping command")
            quote = random.choice(self.life_quotes)
            await event.respond(f"🟢 Bot is alive and kicking!\n\n✨ Here's your daily dose of wisdom:\n\n\"{quote}\"\n\n🤖 Stay awesome!\n\nRadhe Radhe 💞")

        @self.bot.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            sender = await event.get_sender()
            sender_id = sender.id
            self.logger.info(f"Received help command from user {sender_id}")
            commands = self.owner_manager.get_command_list(sender.id)
            await event.respond(f"Available Commands:\n{commands}")

        @self.bot.on(events.NewMessage(pattern='/add_owner'))
        async def add_owner_handler(event):
            sender = await event.get_sender()
            if not self.owner_manager.is_head_owner(sender.id):
                await event.respond("❌ Only head owner can add owners.")
                return

            try:
                owner_id = event.text.split()[1]
                if self.owner_manager.add_owner(owner_id, OwnerLevel.OWNER):
                    await event.respond(f"✅ Successfully added owner: {owner_id}")
                else:
                    await event.respond("❌ Failed to add owner. Please check the ID.")
            except IndexError:
                await event.respond("⚠️ Please provide owner ID: /add_owner <user_id>")

        @self.bot.on(events.NewMessage(pattern='/remove_owner'))
        async def remove_owner_handler(event):
            sender = await event.get_sender()
            if not self.owner_manager.is_head_owner(sender.id):
                await event.respond("❌ Only head owner can remove owners.")
                return

            try:
                owner_id = event.text.split()[1]
                if self.owner_manager.remove_owner(owner_id, OwnerLevel.OWNER):
                    await event.respond(f"✅ Successfully removed owner: {owner_id}")
                else:
                    await event.respond("❌ Failed to remove owner. Please check the ID.")
            except IndexError:
                await event.respond("⚠️ Please provide owner ID: /remove_owner <user_id>")

        @self.bot.on(events.NewMessage(pattern='/list_owners'))
        async def list_owners_handler(event):
            sender = await event.get_sender()
            if not self.owner_manager.is_head_owner(sender.id):
                await event.respond("❌ Only head owner can view owner list.")
                return

            owners = self.owner_manager.owners['owner']
            if owners:
                await event.respond(f"👥 Current owners:\n{', '.join(map(str, owners))}")
            else:
                await event.respond("ℹ️ No owners currently registered.")

        @self.bot.on(events.NewMessage(pattern='/add_channel'))
        async def add_channel_handler(event):
            sender = await event.get_sender()
            if not (self.owner_manager.is_head_owner(sender.id) or self.owner_manager.is_manager(sender.id)):
                await event.respond("❌ You need to be an owner or head owner to add channels.")
                return

            try:
                channel = event.text.split()[1]
                sessions = self.session_manager.get_all_sessions()
                if not sessions:
                    await event.respond("⚠️ No available sessions to join channel.")
                    return

                session_string = self.session_manager.load_session(sessions[0])
                client = TelegramClient(StringSession(), self.api_id, self.api_hash)
                await client.connect()

                if await self.channel_viewer.join_channel(channel, client, is_group=False):
                    await event.respond(f"✅ Successfully joined channel: {channel}")
                else:
                    await event.respond(f"❌ Failed to join channel: {channel}")

                await client.disconnect()

            except IndexError:
                await event.respond("⚠️ Please provide a channel username: /add_channel <username>")
            except Exception as e:
                await event.respond(f"❌ Error: {str(e)}")

        @self.bot.on(events.NewMessage(pattern='/add_group'))
        async def add_group_handler(event):
            sender = await event.get_sender()
            if not (self.owner_manager.is_head_owner(sender.id) or self.owner_manager.is_manager(sender.id)):
                await event.respond("❌ You need to be an owner or head owner to add groups.")
                return

            try:
                group = event.text.split()[1]
                sessions = self.session_manager.get_all_sessions()
                if not sessions:
                    await event.respond("⚠️ No available sessions to join group.")
                    return

                session_string = self.session_manager.load_session(sessions[0])
                client = TelegramClient(StringSession(), self.api_id, self.api_hash)
                await client.connect()

                if await self.channel_viewer.join_channel(group, client, is_group=True):
                    await event.respond(f"✅ Successfully joined group: {group}")
                else:
                    await event.respond(f"❌ Failed to join group: {group}")

                await client.disconnect()

            except IndexError:
                await event.respond("⚠️ Please provide a group username or invite link: /add_group <username/invite>")
            except Exception as e:
                await event.respond(f"❌ Error: {str(e)}")


        @self.bot.on(events.NewMessage(pattern='/add_id'))
        async def add_account_handler(event):
            sender = await event.get_sender()
            if not (self.owner_manager.is_head_owner(sender.id) or self.owner_manager.is_manager(sender.id)):
                await event.respond("❌ You need to be an owner or head owner to add accounts.")
                return

            try:
                phone = event.text.split()[1]
                client = await self.session_manager.create_session(phone)
                await event.respond(f"📱 Please enter the code sent to {phone}")

                self.session_manager.pending_sessions[sender.id] = {
                    'client': client,
                    'phone': phone
                }

            except IndexError:
                await event.respond("⚠️ Please provide a phone number: /add_id <phone>")
            except Exception as e:
                await event.respond(f"❌ Error: {str(e)}")

        @self.bot.on(events.NewMessage(pattern=r'^\d{5}$'))
        async def code_handler(event):
            sender = await event.get_sender()
            if sender.id not in self.session_manager.pending_sessions:
                return

            try:
                session_data = self.session_manager.pending_sessions[sender.id]
                client = session_data['client']
                phone = session_data['phone']

                await client.sign_in(phone, event.text)
                encrypted_session = encrypt_data(client.session.save())
                self.session_manager.save_session(phone, encrypted_session)

                await event.respond("Account successfully added!")
                del self.session_manager.pending_sessions[sender.id]

            except SessionPasswordNeededError:
                await event.respond("This account has 2FA enabled. Please send the password.")
            except PhoneCodeInvalidError:
                await event.respond("Invalid code. Please try again.")
            except Exception as e:
                await event.respond(f"Error: {str(e)}")

        @self.bot.on(events.NewMessage(pattern='/view_stats'))
        async def stats_handler(event):
            sender = await event.get_sender()
            if not self.owner_manager.is_owner(sender.id):
                return

            stats = self.session_manager.get_viewing_stats()
            await event.respond(f"Current viewing statistics:\n{stats}")

        @self.bot.on(events.NewMessage(pattern='/system_stats'))
        async def system_stats_handler(event):
            sender = await event.get_sender()
            if not (self.owner_manager.is_head_owner(sender.id) or self.owner_manager.is_manager(sender.id)):
                return

            # Get statistics from all components
            session_stats = self.session_manager.get_viewing_stats()
            chat_stats = self.channel_viewer.get_chat_stats()
            proxy_stats = self.proxy_manager.get_proxy_stats()

            stats_message = (
                f"📊 System Statistics\n\n"
                f"👥 Sessions:\n"
                f"  • Total Sessions: {session_stats['total_sessions']}\n"
                f"  • Active Today: {session_stats['active_today']}\n"
                f"  • Total Views: {session_stats['total_views']}\n\n"
                f"📺 Channels & Groups:\n"
                f"  • Total Channels: {chat_stats['channels']}\n"
                f"  • Total Groups: {chat_stats['groups']}\n"
                f"  • Active Channels: {chat_stats['active_channels']}\n"
                f"  • Active Groups: {chat_stats['active_groups']}\n\n"
                f"🌐 Proxies:\n"
                f"  • Total Proxies: {proxy_stats['total_proxies']}\n"
                f"  • Available: {proxy_stats['available_proxies']}\n"
                f"  • Failed: {proxy_stats['failed_proxies']}\n"
                f"  • Success Rate: {proxy_stats['success_rate']}\n\n"
                f"⏰ Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            await event.respond(stats_message)

        @self.bot.on(events.NewMessage(pattern='/owner_status'))
        async def owner_status_handler(event):
            sender = await event.get_sender()
            sender_id = sender.id

            is_head = self.owner_manager.is_head_owner(sender_id)
            is_manager = self.owner_manager.is_manager(sender_id)
            is_owner = self.owner_manager.is_owner(sender_id)

            status_msg = f"Your ID: {sender_id}\n"
            if is_head:
                status_msg += "Role: Head Owner\n"
            elif is_manager:
                status_msg += "Role: Owner\n"
            elif is_owner:
                status_msg += "Role: Normal User\n"
            else:
                status_msg += "Role: Not Authorized\n"

            await event.respond(status_msg)

        @self.bot.on(events.NewMessage)
        async def message_handler(event):
            # First check if it's a private message
            if event.is_private:
                sender = await event.get_sender()
                sender_id = sender.id

                # If user is in chat mode and this isn't a command
                if sender_id in self.chat_sessions and not event.message.text.startswith('/'):
                    self.logger.info(f"Processing chat message from user {sender_id}")
                    # Check if Gemini is available
                    if not hasattr(self, 'gemini_available') or not self.gemini_available:
                        await event.respond(
                            "⚠️ Gemini AI is currently unavailable. Use /stop to exit chat mode.\n"
                            "Please contact the bot administrator to fix the Gemini API integration."
                        )
                        # Remove user from chat sessions to prevent further errors
                        if sender_id in self.chat_sessions:
                            del self.chat_sessions[sender_id]
                        return
                        
                    try:
                        text = event.message.text
                        chat = self.chat_sessions[sender_id]
                        text_lower = text.lower()

                        # Send typing indicator
                        async with self.bot.action(event.chat_id, 'typing'):
                            # Check if it's an image generation request
                            if any(text_lower.startswith(prefix) for prefix in ['generate image', 'create image', 'make image']):
                                prompt = text.split(' ', 2)[2]  # Get the prompt after command
                                self.logger.info(f"Image description request from user {sender_id}: {prompt}")
                                await event.respond("🎨 Creating an artistic description based on your prompt... Please wait.")

                                try:
                                    response = chat.send_message(
                                        f"Create a detailed and creative description of this image: {prompt}. "
                                        "Describe it as if you're a professional artist explaining their masterpiece. "
                                        "Focus on colors, composition, mood, and artistic elements."
                                    )
                                    if response and hasattr(response, 'text') and response.text:
                                        await event.respond(
                                            f"🖼️ Here's an artistic vision for '{prompt}':\n\n{response.text}\n\n"
                                            "Note: This is an artistic description to inspire your imagination."
                                        )
                                    else:
                                        await event.respond("I couldn't generate a description. Please try a different prompt.")
                                except Exception as e:
                                    self.logger.error(f"Error in image description: {str(e)}")
                                    await event.respond(
                                        "I apologize, but I encountered an error while creating the description. "
                                        "Please try a different prompt or try again later."
                                    )
                                return

                            # Regular chat response
                            try:
                                self.logger.info(f"Sending message to Gemini for user {sender_id}")
                                response = chat.send_message(text)
                                
                                if response and hasattr(response, 'text') and response.text:
                                    # Split long responses to avoid Telegram limits
                                    if len(response.text) > 4000:
                                        chunks = [response.text[i:i+4000] for i in range(0, len(response.text), 4000)]
                                        for chunk in chunks:
                                            await event.respond(chunk)
                                    else:
                                        await event.respond(response.text)
                                else:
                                    await event.respond(
                                        "I couldn't generate a response. Could you please rephrase your message?"
                                    )
                            except Exception as e:
                                self.logger.error(f"Error in chat response: {str(e)}")
                                await event.respond(
                                    "I encountered an error while processing your message. Please try again."
                                )
                        return
                    except Exception as e:
                        self.logger.error(f"Error in chat mode: {str(e)}")
                        await event.respond("Sorry, there was an error processing your message. Please try again.")
                        return

            # Handle channel/group messages for auto-view
            if event.chat_id in self.channel_viewer.channels:
                self.logger.info(f"Processing message {event.id} from channel {event.chat_id}")
                await self.channel_viewer.rotate_session(event.chat_id, event.id)
            elif event.chat_id in self.channel_viewer.groups:
                self.logger.info(f"Processing message {event.id} from group {event.chat_id}")
                await self.channel_viewer.rotate_session(event.chat_id, event.id)

        @self.bot.on(events.NewMessage(pattern='/contact'))
        async def contact_handler(event):
            sender = await event.get_sender()
            sender_id = sender.id
            self.logger.info(f"Contact command received from user {sender_id}")
            contact_text = (
                f"📞 Contact Information:\n\n"
                f"👑 Owner ID: @owner_of_bollywood_house\n"
                f"🔗 Contact Link: https://taplink.cc/deepdey.official\n\n"
                f"✨ Get premium access for only 4000 rs and boost your views!\n"
                f"• Add unlimited Telegram accounts\n"
                f"• Automatic views on all posts\n"
                f"• Smart anti-ban protection\n"
                f"• 24/7 automated viewing\n\n"
                f"💬 Send message 'add me as owner' to get started!"
            )
            self.logger.info(f"Sending contact information to user {sender_id}")
            await event.respond(contact_text)

        @self.bot.on(events.NewMessage(pattern='/broadcast'))
        async def broadcast_handler(event):
            sender = await event.get_sender()
            if not self.owner_manager.is_head_owner(sender.id):
                await event.respond("❌ Only head owner can broadcast messages.")
                return

            try:
                # Get the message to broadcast (everything after /broadcast)
                message = event.text.split(' ', 1)[1]

                # Keep track of successful/failed sends
                success_count = 0
                fail_count = 0

                # Send to all users who have interacted with the bot
                for user_id in self.all_users:
                    try:
                        await self.bot.send_message(user_id, f"📢 Broadcast Message:\n\n{message}")
                        success_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to send broadcast to {user_id}: {str(e)}")
                        fail_count += 1

                # Report results to head owner
                await event.respond(
                    f"📊 Broadcast Results:\n"
                    f"✅ Successfully sent: {success_count}\n"
                    f"❌ Failed to send: {fail_count}"
                )
            except IndexError:
                await event.respond("⚠️ Please provide a message to broadcast: /broadcast <message>")


        self.logger.info("Bot is ready! Waiting for commands...")
        await self.bot.run_until_disconnected()

    def run(self):
        self.logger.info("Starting bot event loop...")
        self.bot.loop.run_until_complete(self.start())

if __name__ == "__main__":
    try:
        bot = TelegramViewBot()
        bot.run()
    except Exception as e:
        print(f"Critical error: {str(e)}")
        raise
