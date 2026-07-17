from typing import List, Dict
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from models.base import UserDownload
from services.llm_service import LLMService

_llm_service_singleton: LLMService | None = None

def _get_llm_service() -> LLMService:
    global _llm_service_singleton
    if _llm_service_singleton is None:
        _llm_service_singleton = LLMService()
    return _llm_service_singleton

class RecommendationService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.llm_service = _get_llm_service()

    async def get_user_history(self, user_id: int):
        """
        Fetches the user's download history, separated into likely liked and disliked songs.
        We infer 'liked' from positive ratings (1) or neutral downloads (no rating).
        We infer 'disliked' from negative ratings (-1).
        """
        # Fetch liked/neutral songs (UserDownload.user_rating != -1)
        # We assume recent downloads are more relevant, so we take the last 50.
        liked_query = (
            select(UserDownload.artist, UserDownload.title)
            .where(UserDownload.user_id == user_id)
            .where((UserDownload.user_rating == 1) | (UserDownload.user_rating.is_(None)))
            .order_by(desc(UserDownload.downloaded_at))
            .limit(50)
        )
        
        disliked_query = (
            select(UserDownload.artist, UserDownload.title)
            .where(UserDownload.user_id == user_id)
            .where(UserDownload.user_rating == -1)
            .order_by(desc(UserDownload.downloaded_at))
            .limit(20)
        )

        liked_results = (await self.db.execute(liked_query)).all()
        disliked_results = (await self.db.execute(disliked_query)).all()

        liked_songs = [f"{row.artist} - {row.title}" for row in liked_results if row.artist and row.title]
        disliked_songs = [f"{row.artist} - {row.title}" for row in disliked_results if row.artist and row.title]

        return liked_songs, disliked_songs

    async def get_recommendations(self, user_id: int) -> List[Dict[str, str]]:
        """
        Orchestrates the recommendation process:
        1. Get user history
        2. Call LLM
        3. Return results
        """
        liked_songs, disliked_songs = await self.get_user_history(user_id)
        
        if not liked_songs:
            # We could return generic trending charts here or ask user to download some songs first
            return []

        recommendations = await self.llm_service.generate_recommendations(liked_songs, disliked_songs)
        
        return recommendations
