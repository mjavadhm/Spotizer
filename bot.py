import os
import shutil
import logging
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession

def cleanup_workdirs(dirs=("downloads", "temp")):
    """موقع استارت بات، پوشههای کاری رو خالی میکنه."""
    for d in dirs:
        try:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            print(f"cleanup_workdirs failed for {d}: {e}")

cleanup_workdirs()

load_dotenv()
API_BASE_URL = 'http://localhost:8081'

try:
    TOKEN = os.getenv('BOT_TOKEN')
    api_server = TelegramAPIServer.from_base(base=API_BASE_URL)
    session = AiohttpSession(api=api_server)
    bot = Bot(token=TOKEN, session=session)
except Exception as e:
    logging.error(e)
    
