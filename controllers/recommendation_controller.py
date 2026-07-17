import logging
from database.session import async_session_maker
from services.recommendation_service import RecommendationService
from services.deezer_service import DeezerAPIClient

logger = logging.getLogger(__name__)

class RecommendationController:
    @staticmethod
    async def recommend_music(user_id: int):
        """
        خروجی: (success, text, found_tracks)
        found_tracks: [{'deezer_id': str, 'title': str, 'artist': str}, ...]
        """
        async with async_session_maker() as session:
            try:
                service = RecommendationService(session)
                recommendations = await service.get_recommendations(user_id)

                if not recommendations:
                    return False, "We don't have enough history to recommend music yet. Download some songs and rate them!", []

                found, not_found = [], []
                for rec in recommendations:
                    artist = (rec.get('artist') or '').strip()
                    title = (rec.get('title') or '').strip()
                    if not title:
                        continue
                    query = f"{artist} {title}".strip()
                    try:
                        results = await DeezerAPIClient.search(query, "track", limit=1)
                    except Exception as e:
                        logger.warning(f"Deezer resolve failed for '{query}': {e}")
                        results = []

                    if results:
                        r = results[0]
                        found.append({
                            'deezer_id': r['id'],
                            'title': r['name'],
                            'artist': r.get('main_artist', artist),
                        })
                    else:
                        not_found.append(f"{artist} - {title}")

                # متن پیام
                lines = ["🎵 *Recommended for You* 🎵", "Tap a track below to download 👇"]
                if not_found:
                    lines.append("\n_Couldn't find on Deezer:_")
                    lines += [f"• {x}" for x in not_found]
                text = "\n".join(lines)

                if not found and not_found:
                    # هیچکدوم روی Deezer نبود
                    return True, text + "\n\nTry /recommend again for other picks.", []

                return True, text, found

            except Exception as e:
                logger.error(f"Error generating recommendations for user {user_id}: {e}", exc_info=True)
                return False, "An error occurred while generating recommendations. Please try again later.", []
