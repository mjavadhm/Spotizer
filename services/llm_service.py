import os
import json
from typing import List, Dict, Any, Optional

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv()

class Recommendation(BaseModel):
    artist: str = Field(description="The name of the music artist")
    title: str = Field(description="The title of the song")

class LLMService:
    def __init__(self):
        self._setup_chain()

    def _setup_chain(self):
        # Default to Gemini, but implementation allows for easy swapping
        # Ensure GEMINI_API_KEY is in your .env
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # We might want to log a warning here, but for now we'll assume it's set or will be set
            pass

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.7,
            google_api_key=api_key,
            convert_system_message_to_human=True # Sometimes needed for certain models
        )

        self.parser = JsonOutputParser(pydantic_object=Recommendation)

        self.prompt = PromptTemplate(
            template="""You are a knowledgeable music recommendation assistant.
Based on the user's listening history below, recommend 5 new songs that they are likely to enjoy.
Focus on similar genres, moods, and artists, but do not recommend songs from the input list.

Liked Songs (High rating or frequent listens):
{liked_songs}

Disliked Songs (Explicitly disliked):
{disliked_songs}

{format_instructions}

Return ONLY the JSON array.
""",
            input_variables=["liked_songs", "disliked_songs"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

        self.chain = self.prompt | self.llm | self.parser

    async def generate_recommendations(self, liked_songs: List[str], disliked_songs: List[str]) -> List[Dict[str, str]]:
        """
        Generates music recommendations based on liked and disliked song lists.
        """
        if not liked_songs:
            # Default fallback if no history provided
            liked_songs = ["Popular Pop/Rock songs"]
        
        try:
            response = await self.chain.ainvoke({
                "liked_songs": "\n".join(f"- {song}" for song in liked_songs),
                "disliked_songs": "\n".join(f"- {song}" for song in disliked_songs) if disliked_songs else "None"
            })
            
            # Ensure response is a list
            if isinstance(response, dict):
                # Sometimes the parser returns a single dict if the model only produces one object
                response = [response]
            elif not isinstance(response, list):
                # Fallback empty list if parsing fails in a weird way
                return []
                
            return response
            
        except Exception as e:
            # Log the error properly in a real aplication
            print(f"Error generating recommendations: {e}")
            return []
