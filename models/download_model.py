from typing import Dict, List, Optional, Any
from datetime import datetime
from database.connection import get_connection
from logger import get_logger

logger = get_logger(__name__)

class DownloadModel:
    def add_download(self, user_id: int, track_info: Dict[str, Any], file_path: str, quality: str) -> bool:
        """Add a new download record"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Extract track info
                    deezer_id = track_info.get('id')
                    content_type = 'track'  # Default to track for now
                    title = track_info.get('title')
                    artist = track_info.get('artist', {}).get('name') if track_info.get('artist') else None
                    album = track_info.get('album', {}).get('title') if track_info.get('album') else None
                    duration = track_info.get('duration')
                    
                    # Check if this download exists for this user
                    cur.execute("""
                    SELECT download_id FROM user_downloads 
                    WHERE user_id = %s AND deezer_id = %s AND content_type = %s AND quality = %s
                    """, (user_id, deezer_id, content_type, quality))
                    
                    download_exists = cur.fetchone()
                    
                    if download_exists:
                        # Update existing download
                        cur.execute("""
                        UPDATE user_downloads 
                        SET file_id = %s, quality = %s, url = %s, title = %s, artist = %s, 
                            album = %s, duration = %s, file_name = %s, downloaded_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND deezer_id = %s AND content_type = %s
                        """, (
                            file_path, quality, 
                            track_info.get('link'), title, artist, album, duration,
                            file_path.split('/')[-1],
                            user_id, deezer_id, content_type
                        ))
                        logger.info(f"Updated download record for track {deezer_id} (User: {user_id})")
                    else:
                        # Add new download
                        cur.execute("""
                        INSERT INTO user_downloads (
                            user_id, deezer_id, content_type, file_id, quality,
                            url, title, artist, album, duration, file_name
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            user_id, deezer_id, content_type, file_path, quality,
                            track_info.get('link'), title, artist, album, duration,
                            file_path.split('/')[-1]
                        ))
                        logger.info(f"Added new download record for track {deezer_id} (User: {user_id})")
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to add/update download record: {str(e)}", exc_info=True)
            return False

    def get_download_by_deezer_id(self, deezer_id: int, content_type: str = None, 
                                 quality: str = None) -> Optional[Dict[str, Any]]:
        """Get a specific download by Deezer ID"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                    SELECT file_id, quality, url, title, artist, album, duration, 
                           downloaded_at, file_name 
                    FROM user_downloads 
                    WHERE deezer_id = %s
                    """
                    params = [deezer_id]
                    
                    if content_type:
                        query += " AND content_type = %s"
                        params.append(content_type)
                    
                    if quality:
                        query += " AND quality = %s"
                        params.append(quality)
                    
                    cur.execute(query, params)
                    download = cur.fetchone()
                    
                    if download:
                        logger.info(f"Retrieved download record for track {deezer_id}")
                        return {
                            'file_id': download[0],
                            'quality': download[1],
                            'url': download[2],
                            'title': download[3],
                            'artist': download[4],
                            'album': download[5],
                            'duration': download[6],
                            'downloaded_at': download[7],
                            'file_name': download[8]
                        }
                    logger.info(f"No download record found for track {deezer_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to retrieve download record: {str(e)}", exc_info=True)
            return None

    def get_user_downloads(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get a user's download history"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                    SELECT deezer_id, content_type, file_id, quality, url, title, artist, album, 
                           duration, downloaded_at, file_name
                    FROM user_downloads
                    WHERE user_id = %s
                    ORDER BY downloaded_at DESC
                    LIMIT %s OFFSET %s
                    """, (user_id, limit, offset))
                    
                    downloads = []
                    for row in cur.fetchall():
                        downloads.append({
                            'deezer_id': row[0],
                            'content_type': row[1],
                            'file_id': row[2],
                            'quality': row[3],
                            'url': row[4],
                            'title': row[5],
                            'artist': row[6],
                            'album': row[7],
                            'duration': row[8],
                            'downloaded_at': row[9],
                            'file_name': row[10]
                        })
                    logger.info(f"Retrieved {len(downloads)} download records for user {user_id}")
                    return downloads
                    
        except Exception as e:
            logger.error(f"Failed to retrieve user downloads: {str(e)}", exc_info=True)
            return []

    def update_download_count(self, deezer_id: int) -> bool:
        """Update download count for a track"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                    UPDATE tracks 
                    SET download_count = download_count + 1,
                        last_downloaded = CURRENT_TIMESTAMP
                    WHERE track_id = %s
                    """, (deezer_id,))
                    conn.commit()
                    logger.info(f"Updated download count for track {deezer_id}")
                    return True
        except Exception as e:
            logger.error(f"Failed to update download count: {str(e)}", exc_info=True)
            return False

    def get_popular_downloads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular downloads"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                    SELECT track_id, title, artist, album, download_count
                    FROM tracks
                    ORDER BY download_count DESC
                    LIMIT %s
                    """, (limit,))
                    
                    popular = []
                    for row in cur.fetchall():
                        popular.append({
                            'track_id': row[0],
                            'title': row[1],
                            'artist': row[2],
                            'album': row[3],
                            'download_count': row[4]
                        })
                    logger.info(f"Retrieved {len(popular)} popular downloads")
                    return popular
        except Exception as e:
            logger.error(f"Failed to retrieve popular downloads: {str(e)}", exc_info=True)
            return []

    def get_track_by_deezer_id_quality(self, user_id, deezer_id, quality):
        """Get track by deezer id and quality"""
        try:
            deezer_id = str(deezer_id)
            with get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                            SELECT track_id, file_id, title, artist, album, download_count, quality, duration, file_name
                            FROM tracks
                            WHERE track_id = %s AND quality = %s
                        """
                    params = [deezer_id, quality]
                    cur.execute(query, params)
                    row = cur.fetchone()
                    if row:
                        logger.info(f"Retrieved track record for Deezer ID {deezer_id} with quality {quality}")
                        return {
                            'track_id': row[0],
                            'file_id': row[1],
                            'title': row[2],
                            'artist': row[3],
                            'album': row[4],
                            'download_count': row[5],
                            'quality': row[6],
                            'duration': row[7],
                            'file_name': row[8]
                        }
                    logger.info(f"No track found for Deezer ID {deezer_id} with quality {quality}")
                    return None
        except Exception as e:
            logger.error(f"Failed to retrieve track: {str(e)}", exc_info=True)
            return None
    
    def add_track(self, user_id, deezer_id, content_type, file_id, quality, title, artist=None, album=None, duration=None, file_name=None, url=None):
        """Add a new track to the database"""
        try:
            deezer_id = str(deezer_id)
            with get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                    INSERT INTO tracks (track_id, content_type, file_id, quality, title, artist, album, duration, file_name, url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params = [deezer_id, content_type, file_id, quality, title, artist, album, duration, file_name, url]
                    cur.execute(query, params)
                    conn.commit()
                    logger.info(f"Added new track record: {title} (Deezer ID: {deezer_id}, User: {user_id})")
                    return True
        except Exception as e:
            logger.error(f"Failed to add track record: {str(e)}", exc_info=True)
            return False
