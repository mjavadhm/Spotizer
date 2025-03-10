import os
import logging
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession
load_dotenv()
API_BASE_URL = 'http://89.22.236.107:9097'

try:
    TOKEN = os.getenv('BOT_TOKEN')
    api_server = TelegramAPIServer.from_base(base=API_BASE_URL)
    session = AiohttpSession(api=api_server)
    bot = Bot(token=TOKEN, session=session)
except Exception as e:
    logging.error(e)
    