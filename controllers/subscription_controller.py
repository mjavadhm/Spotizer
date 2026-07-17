import logging
from sqlalchemy import select, delete
from database.session import async_session_maker
from models.base import ArtistSubscription
from services.deezer_service import DeezerAPIClient

logger = logging.getLogger(__name__)

def _valid_date(a):
    d = a.get('release_date') or ''
    return d if len(d) >= 10 and d[:4].isdigit() else ''

class SubscriptionController:
    @staticmethod
    async def subscribe(user_id: int, artist_id: str, artist_name: str = None):
        async with async_session_maker() as session:
            try:
                existing = (await session.execute(
                    select(ArtistSubscription).where(
                        ArtistSubscription.user_id == user_id,
                        ArtistSubscription.artist_id == str(artist_id),
                    )
                )).scalar_one_or_none()
                if existing:
                    return False, "You're already following this artist."

                # اسنپشات آخرین ریلیز، تا فقط ریلیزهای «آینده» خبر داده بشن
                last_id, last_date = None, None
                try:
                    albums = await DeezerAPIClient.get_artist_albums(str(artist_id))
                    if albums:
                        latest = max(albums, key=_valid_date)
                        last_id = latest['id']
                        last_date = _valid_date(latest)
                        if not artist_name:
                            artist_name = latest.get('artist')
                except Exception as e:
                    logger.warning(f"Snapshot failed for artist {artist_id}: {e}")

                session.add(ArtistSubscription(
                    user_id=user_id,
                    artist_id=str(artist_id),
                    artist_name=artist_name,
                    last_release_id=last_id,
                    last_release_date=last_date,
                ))
                await session.commit()
                return True, f"🔔 You're now following {artist_name or 'this artist'}!"
            except Exception as e:
                await session.rollback()
                logger.error(f"subscribe error: {e}", exc_info=True)
                return False, "Error subscribing."

    @staticmethod
    async def unsubscribe(user_id: int, artist_id: str):
        async with async_session_maker() as session:
            try:
                await session.execute(delete(ArtistSubscription).where(
                    ArtistSubscription.user_id == user_id,
                    ArtistSubscription.artist_id == str(artist_id),
                ))
                await session.commit()
                return True, "Unsubscribed."
            except Exception as e:
                await session.rollback()
                logger.error(f"unsubscribe error: {e}", exc_info=True)
                return False, "Error unsubscribing."

    @staticmethod
    async def list_subscriptions(user_id: int):
        async with async_session_maker() as session:
            return (await session.execute(
                select(ArtistSubscription).where(ArtistSubscription.user_id == user_id)
            )).scalars().all()
