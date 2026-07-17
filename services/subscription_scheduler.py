import asyncio
import logging
from sqlalchemy import select, update
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.session import async_session_maker
from models.base import ArtistSubscription
from services.deezer_service import DeezerAPIClient
from controllers.subscription_controller import _valid_date

logger = logging.getLogger(__name__)
CHECK_INTERVAL = 60 * 60 * 6  # هر ۶ ساعت

async def _notify(bot, user_id, album, artist_name):
    try:
        text = (f"🔔 New release from *{artist_name or album.get('artist','')}*!\n\n"
                f"💿 {album['name']} ({_valid_date(album) or '—'})")
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬇️ Download", callback_data=f"download:album:{album['id']}")
        ]])
        await bot.send_message(user_id, text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"notify failed for user {user_id}: {e}")

async def _check_once(bot):
    async with async_session_maker() as session:
        subs = (await session.execute(select(ArtistSubscription))).scalars().all()

    # گروهبندی بر اساس آرتیست → هر آرتیست فقط یکبار از API پرسیده میشه
    by_artist = {}
    for s in subs:
        by_artist.setdefault(s.artist_id, []).append(s)

    for artist_id, subscribers in by_artist.items():
        try:
            albums = await DeezerAPIClient.get_artist_albums(artist_id)
        except Exception as e:
            logger.warning(f"release-check failed for artist {artist_id}: {e}")
            continue
        if not albums:
            continue

        latest = max(albums, key=_valid_date)
        latest_id = str(latest['id'])
        latest_date = _valid_date(latest)

        for s in subscribers:
            is_new = (s.last_release_id != latest_id) and \
                     (not s.last_release_date or latest_date > s.last_release_date)
            if is_new:
                await _notify(bot, s.user_id, latest, s.artist_name)
            # پوینتر رو بهروز کن (چه خبر دادیم چه نه)
            async with async_session_maker() as session:
                await session.execute(update(ArtistSubscription)
                    .where(ArtistSubscription.id == s.id)
                    .values(last_release_id=latest_id, last_release_date=latest_date))
                await session.commit()

        await asyncio.sleep(0.5)  # مهربون با rate limit دیزر

async def run_release_checker(bot):
    logger.info("Release checker started")
    while True:
        try:
            await _check_once(bot)
        except Exception as e:
            logger.error(f"release checker loop error: {e}", exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL)
