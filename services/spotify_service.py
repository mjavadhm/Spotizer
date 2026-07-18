import re
import json
import asyncio
from typing import Optional, Tuple, Dict, Any, List

import aiohttp

from logger import get_logger

logger = get_logger(__name__)

class SpotifyService:
    """Resolve Spotify links to a plain tracklist WITHOUT the official API.

    We scrape the public embed page (open.spotify.com/embed/{type}/{id}),
    which ships a JSON payload in a <script id="__NEXT_DATA__"> tag that
    contains the title/artist (and, for albums/playlists, the whole
    trackList). No API key / OAuth required.
    """

    EMBED_URL = "https://open.spotify.com/embed/{type}/{sid}"
    OEMBED_URL = "https://open.spotify.com/oembed"

    _URL_RE = re.compile(
        r"open\.spotify\.com/(?:intl-[a-z]{2}/)?(track|album|playlist)/([A-Za-z0-9]+)"
    )
    _URI_RE = re.compile(r"spotify:(track|album|playlist):([A-Za-z0-9]+)")

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        )
    }

    _session: Optional[aiohttp.ClientSession] = None

    @classmethod
    async def _get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession(headers=cls._HEADERS)
        return cls._session

    @classmethod
    def is_spotify_url(cls, url: str) -> bool:
        if not url:
            return False
        u = url.lower()
        return "open.spotify.com" in u or u.startswith("spotify:")

    @classmethod
    def parse_url(cls, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Return (content_type, spotify_id) or (None, None)."""
        try:
            m = cls._URL_RE.search(url) or cls._URI_RE.search(url)
            if not m:
                return None, None
            return m.group(1), m.group(2)
        except Exception as e:
            logger.error(f"Error parsing Spotify URL {url}: {e}")
            return None, None

    # -- payload extraction ------------------------------------------------

    @staticmethod
    def _extract_next_data(html: str) -> Optional[dict]:
        """Pull the JSON inside <script id=\"__NEXT_DATA__\">."""
        if not html:
            return None
        m = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except Exception as e:
            logger.warning(f"Failed to parse __NEXT_DATA__ JSON: {e}")
            return None

    @staticmethod
    def _find_entity(data: Any) -> Optional[dict]:
        """Locate the entity object (has title + optional trackList) in the
        payload. We try the known path first, then fall back to a deep scan
        so we survive small structure changes."""
        # Known path: props.pageProps.state.data.entity
        try:
            entity = (
                data["props"]["pageProps"]["state"]["data"]["entity"]
            )
            if isinstance(entity, dict) and entity.get("title"):
                return entity
        except Exception:
            pass

        # Deep fallback: first dict that has both 'title' and 'trackList',
        # otherwise first dict with 'title' + 'subtitle'.
        best = None
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("title") and isinstance(node.get("trackList"), list):
                    return node
                if best is None and node.get("title") and "subtitle" in node:
                    best = node
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
        return best

    @staticmethod
    def _norm_track(item: dict) -> Optional[dict]:
        title = item.get("title") or item.get("name")
        if not title:
            return None
        artist = item.get("subtitle") or item.get("artist") or ""
        duration_ms = item.get("duration") or item.get("duration_ms")
        try:
            duration_ms = int(duration_ms) if duration_ms else None
        except Exception:
            duration_ms = None
        return {"title": title, "artist": artist, "duration_ms": duration_ms}

    @classmethod
    def _extract_tracks(cls, entity: Optional[dict], content_type: str) -> List[dict]:
        if not entity:
            return []
        track_list = entity.get("trackList")
        if isinstance(track_list, list) and track_list:
            out = []
            for it in track_list:
                if isinstance(it, dict):
                    t = cls._norm_track(it)
                    if t:
                        out.append(t)
            if out:
                return out
        # Single track embed: the entity itself is the track.
        if content_type == "track":
            t = cls._norm_track(entity)
            return [t] if t else []
        return []

    # -- public API --------------------------------------------------------

    @classmethod
    async def _oembed_title(cls, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        try:
            async with session.get(cls.OEMBED_URL, params={"url": url}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("title")
        except Exception as e:
            logger.warning(f"Spotify oEmbed fallback failed for {url}: {e}")
        return None

    @classmethod
    async def get_tracks(cls, url: str) -> Optional[dict]:
        """Return {'type', 'id', 'name', 'tracks': [{title, artist, duration_ms}]}
        or None if the URL is not a supported Spotify link / could not be read.
        """
        content_type, sid = cls.parse_url(url)
        if not content_type or not sid:
            return None

        session = await cls._get_session()
        embed = cls.EMBED_URL.format(type=content_type, sid=sid)

        html = None
        try:
            async with session.get(embed) as resp:
                if resp.status == 200:
                    html = await resp.text()
                else:
                    logger.warning(f"Spotify embed returned {resp.status} for {embed}")
        except Exception as e:
            logger.error(f"Failed to fetch Spotify embed {embed}: {e}")

        data = cls._extract_next_data(html) if html else None
        entity = cls._find_entity(data) if data else None

        name = None
        if entity:
            name = entity.get("title")
        if not name:
            name = await cls._oembed_title(session, url)
        if not name:
            name = content_type

        tracks = cls._extract_tracks(entity, content_type)

        return {
            "type": content_type,
            "id": sid,
            "name": name,
            "tracks": tracks,
        }
