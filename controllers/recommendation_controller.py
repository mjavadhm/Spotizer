import logging
from database.session import async_session_maker
from services.recommendation_service import RecommendationService
# from data.messages import RECOMMENDATION_HEADER, NO_RECOMMENDATIONS, ERROR_RECOMMENDATION (Removed: file does not exist)

logger = logging.getLogger(__name__)

class RecommendationController:
    @staticmethod
    async def recommend_music(user_id: int):
        """
        Generates music recommendations for the user.
        """
        async with async_session_maker() as session:
            try:
                service = RecommendationService(session)
                recommendations = await service.get_recommendations(user_id)
                
                if not recommendations:
                    return False, "We don't have enough history to recommend music yet. Download some songs and rate them!"

                # Format the response
                # We can make this fancier later with buttons
                msg_parts = ["🎵 *Recommended for You* 🎵\n"]

                
                for idx, rec in enumerate(recommendations, 1):
                    msg_parts.append(f"{idx}. {rec.get('artist', 'Unknown')} - {rec.get('title', 'Unknown')}")
                
                msg_parts.append("\n_Copy the name and search to download!_")
                
                return True, "\n".join(msg_parts)

            except Exception as e:
                logger.error(f"Error generating recommendations for user {user_id}: {e}", exc_info=True)
                return False, "An error occurred while generating recommendations. Please try again later."
