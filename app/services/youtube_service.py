import re
import requests
import hashlib
import time
from typing import List, Dict, Any, Optional
from sqlmodel import Session
from difflib import SequenceMatcher
from datetime import datetime, timezone
from app.core.config import settings
from app.repositories.search import SearchRepository
from app.repositories.songs import SongsRepository
from app.services.cache_service import CacheService
from app.schemas.songs import SongCreate, SongRead
from app.schemas.search import SongSearchResult
from fastapi import HTTPException, status

class YouTubeAPIError(Exception):
    """Exception para errores de YouTube API."""
    pass

class YouTubeService:
    """
    Service para interactuar con YouTube Data API v3.
    
    Funcionalidades:
    - Búsqueda de videos con cache
    - Obtención de detalles de video
    - Normalización y scoring de resultados
    - Logging de búsquedas
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.cache = CacheService(session)
        self.search_repo = SearchRepository(session)
        self.songs_repo = SongsRepository(session)
        
        # Config
        self.api_url = settings.YOUTUBE_API_URL
        self.api_key = settings.YOUTUBE_API_KEY
        self.max_results = settings.YOUTUBE_MAX_RESULTS
        self.min_duration = settings.YOUTUBE_MIN_DURATION_SECONDS
        self.max_duration = settings.YOUTUBE_MAX_DURATION_SECONDS
        self.cache_ttl = settings.SEARCH_CACHE_TTL_MINUTES
        self.forbidden_terms = settings.FORBIDDEN_TERMS

    def search(
        self,
        query: str,
        user_id: Optional[int] = None,
        max_results: Optional[int] = None,
        region_code: Optional[str] = None
    ) -> List[SongSearchResult]:
        """
        Búsqueda de canciones con cache.
        
        Args:
            query: Término de búsqueda
            user_id: ID del usuario (para logging). None = búsqueda anónima
            max_results: Límite de resultados (default: config)
            region_code: Código de región (default: AR)
            
        Returns:
            Lista de resultados ordenados por score
        """
        # Normalizar query
        normalized_q = self._normalize_query(query)
        if not normalized_q:
            return []
        
        # Params para cache key
        params = {
            "max_results": max_results or self.max_results,
            "region": region_code or settings.YOUTUBE_REGION_CODE
        }
        cache_key = self._generate_cache_key(normalized_q, params)
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            print(f"✅ Cache hit: {query}")
            # Log búsqueda (incluso si es cache hit)
            if user_id:
                self._log_search(user_id, query)
            return [SongSearchResult(**item) for item in cached["results"]]
        
        print(f"🔍 YouTube API call: {query}")
        
        try:
            # Fetch video IDs
            video_ids = self._fetch_search_ids(normalized_q, params)
            if not video_ids:
                return []
            
            # Fetch details
            details = self._fetch_video_details(video_ids)
            
            # Process and score
            songs = self._process_and_score(details, normalized_q)
            
            # Cache results (usando model_dump(mode="json") para serializar datetime)
            cache_data = {
                "results": [s.model_dump(mode="json") for s in songs],
                "timestamp": int(time.time() * 1000),
                "query": query
            }
            self.cache.set(cache_key, cache_data, self.cache_ttl)
            
            # Log search
            if user_id:
                self._log_search(user_id, query)
            
            self.session.commit()
            return songs
            
        except YouTubeAPIError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"YouTube API error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search error: {str(e)}"
            )

    def get_video(self, video_id: str) -> Optional[SongRead]:
        """
        Obtiene detalles de un video específico con cache.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Song details o None si no existe
        """
        cache_key = f"video:{video_id}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            print(f"Cache hit: video {video_id}")
            return SongRead(**cached["data"])
        
        print(f"YouTube API call: video {video_id}")
        
        try:
            # Fetch details
            params = {
                "part": "snippet,contentDetails,statistics",
                "id": video_id,
                "key": self.api_key
            }
            response = requests.get(
                f"{self.api_url}/videos",
                params=params,
                timeout=10
            )
            
            self._handle_api_errors(response)
            
            data = response.json()
            if not data.get("items"):
                return None
            
            # Process video
            song_create = self._process_single_video(data["items"][0])
            if not song_create:
                return None
            
            # Upsert to DB
            song_db = self.songs_repo.get_or_create_from_youtube_meta(song_create)
            self.session.commit()
            
            # Cache (serializando datetime a string)
            song_read = SongRead.model_validate(song_db)
            cache_data = {
                "data": song_read.model_dump(mode="json"),
                "timestamp": int(time.time() * 1000)
            }
            self.cache.set(cache_key, cache_data, self.cache_ttl)
            
            return song_read
            
        except YouTubeAPIError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"YouTube API error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video fetch error: {str(e)}"
            )

    def _generate_cache_key(self, query: str, params: Dict[str, Any]) -> str:
        """Genera cache key único para query + params."""
        params_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"search:{query}:{params_hash}"

    def _normalize_query(self, query: str) -> str:
        """Normaliza query: lowercase, quita stopwords y puntuación."""
        if not query:
            return ""
        
        # Lowercase
        query = query.lower().strip()
        
        # Quitar stopwords (español)
        stopwords = r'\b(a|el|la|los|las|de|del|que|y|o|un|una|en|por|para)\b'
        query = re.sub(stopwords, '', query)
        
        # Quitar puntuación
        query = re.sub(r'[,\.\-!?:;()\[\]{}]', '', query)
        
        # Normalizar espacios
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query

    def _fetch_search_ids(self, query: str, params: Dict[str, Any]) -> List[str]:
        """Fetch video IDs desde YouTube search endpoint."""
        search_params = {
            "part": "snippet",
            "type": "video",
            "videoCategoryId": settings.YOUTUBE_CATEGORY_ID,
            "order": "viewCount",
            "relevanceLanguage": "es",
            "regionCode": params.get("region", "AR"),
            "videoDefinition": "high",
            "maxResults": params.get("max_results", self.max_results),
            "q": query,
            "key": self.api_key
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/search",
                params=search_params,
                timeout=10
            )
            
            self._handle_api_errors(response)
            
            data = response.json()
            return [
                item["id"]["videoId"]
                for item in data.get("items", [])
                if item.get("id", {}).get("videoId")
            ]
            
        except requests.RequestException as e:
            raise YouTubeAPIError(f"Network error: {str(e)}")

    def _fetch_video_details(self, video_ids: List[str]) -> Dict[str, Any]:
        """Batch fetch de detalles de videos."""
        if not video_ids:
            return {"items": []}
        
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": self.api_key
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/videos",
                params=params,
                timeout=10
            )
            
            self._handle_api_errors(response)
            return response.json()
            
        except requests.RequestException as e:
            raise YouTubeAPIError(f"Network error: {str(e)}")

    def _handle_api_errors(self, response: requests.Response) -> None:
        """Maneja errores de API de YouTube."""
        if response.status_code == 200:
            return
        
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
        except:
            error_msg = response.text or "Unknown error"
        
        if response.status_code == 403:
            raise YouTubeAPIError(f"Quota exceeded or forbidden: {error_msg}")
        elif response.status_code == 400:
            raise YouTubeAPIError(f"Bad request: {error_msg}")
        elif response.status_code == 404:
            raise YouTubeAPIError(f"Not found: {error_msg}")
        else:
            raise YouTubeAPIError(f"API error ({response.status_code}): {error_msg}")

    def _process_and_score(
        self,
        details: Dict[str, Any],
        query: str
    ) -> List[SongSearchResult]:
        """
        Procesa, filtra, scorea y rankea resultados.
        
        Scoring:
        - 50% views
        - 30% recency
        - 20% match ratio
        + 10% fuzzy match
        + 50% boost para official/topic
        """
        songs = []
        query_terms = query.split()
        
        for item in details.get("items", []):
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            stats = item.get("statistics", {})
            
            title = snippet.get("title", "")
            title_lower = title.lower()
            
            # Filter: Términos prohibidos
            if any(term in title_lower for term in self.forbidden_terms):
                continue
            
            # Filter: Duración
            duration = self._parse_duration(content_details.get("duration", "PT0S"))
            if not (self.min_duration <= duration <= self.max_duration):
                continue
            
            # Scoring factors
            views = int(stats.get("viewCount", 0))
            
            # Age (días desde publicación)
            published_at = snippet.get("publishedAt", "")
            age_days = self._calculate_age_days(published_at)
            
            # Match ratio
            title_terms = title_lower.split()
            match_ratio = (
                sum(1 for term in query_terms if term in title_terms) / len(query_terms)
                if query_terms else 0
            )
            
            # Fuzzy match
            fuzzy_score = SequenceMatcher(None, title_lower, query).ratio()
            
            # Semantic boost
            boost = 1.5 if any(
                phrase in title_lower 
                for phrase in ['official audio', 'official video', 'topic', 'vevo']
            ) else 1.0
            
            # Calculate score
            score = (
                (views / 1000000 * 0.5) +  # Normalize views
                (1 / max(age_days, 1) * 0.3) +
                (match_ratio * 0.2) +
                (fuzzy_score * 0.1)
            ) * boost
            
            # Process song
            song_create = self._process_single_video(item)
            if song_create:
                # Upsert to DB
                song_db = self.songs_repo.get_or_create_from_youtube_meta(song_create)
                
                # Create search result
                song_result = SongSearchResult(
                    **song_db.model_dump(),
                    custom_score=score
                )
                songs.append(song_result)
        
        # Sort by score and add ranking
        songs.sort(key=lambda s: s.custom_score, reverse=True)
        for idx, song in enumerate(songs[:self.max_results], 1):
            song.rank = idx
        
        return songs[:self.max_results]

    def _process_single_video(self, item: Dict[str, Any]) -> Optional[SongCreate]:
        """Parse common fields de un video y seleccionar el mejor thumbnail con debug."""
        try:
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})

            video_id = item.get("id", "")
            if not video_id:
                return None

            # Thumbnails
            thumbnails_data = snippet.get("thumbnails", {})
            thumbnail_url = self._get_best_thumbnail(thumbnails_data)

            # ----- Debugging thumbnails -----
            print(f"[DEBUG] Thumbnails for video {video_id}: {thumbnails_data}")
            print(f"[DEBUG] Selected thumbnail for video {video_id}: {thumbnail_url}")
            # --------------------------------

            thumbnails = {"default": thumbnail_url} if thumbnail_url else None

            # Duration
            duration_iso = content_details.get("duration", "PT0S")
            duration_seconds = self._parse_duration(duration_iso)

            # Published date
            published_at_str = snippet.get("publishedAt", "")
            published_at = self._parse_datetime(published_at_str)

            return SongCreate(
                id=video_id,
                title=snippet.get("title", "Unknown"),
                channel_title=snippet.get("channelTitle"),
                duration=str(duration_seconds),
                thumbnails=thumbnails,
                published_at=published_at
            )

        except Exception as e:
            print(f"Error processing video {item.get('id')}: {e}")
            return None

    def _log_search(self, user_id: int, query: str) -> None:
        """Log búsqueda en history."""
        try:
            self.search_repo.log_search(user_id, query)
        except Exception as e:
            print(f"Error logging search: {e}")

    # Helpers
    
    def _get_best_thumbnail(self, thumbnails: Dict[str, Any]) -> str:
        """Obtiene la mejor calidad de thumbnail disponible."""
        priority = ['maxres', 'standard', 'high', 'medium', 'default']
        for key in priority:
            if thumbnails.get(key, {}).get("url"):
                return thumbnails[key]["url"]
        return ""

    def _parse_duration(self, duration_iso: str) -> int:
        """
        Parse ISO 8601 duration (PT1H2M3S) a segundos.
        
        Args:
            duration_iso: Duration en formato ISO (e.g., "PT3M45S")
            
        Returns:
            Duración en segundos
        """
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if not match:
            return 0
        
        hours, minutes, seconds = match.groups(default='0')
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """
        Parse datetime de YouTube (ISO 8601).
        
        Formatos soportados:
        - 2024-01-01T12:00:00Z
        - 2024-01-01T12:00:00.123Z
        - 2024-01-01T12:00:00+00:00
        """
        if not datetime_str:
            return None
        
        # Reemplazar Z con +00:00 para parsing uniforme
        datetime_str = datetime_str.replace('Z', '+00:00')
        
        try:
            # Intentar con fromisoformat (Python 3.7+)
            return datetime.fromisoformat(datetime_str)
        except:
            # Fallback manual
            try:
                # Sin milliseconds
                return datetime.strptime(
                    datetime_str.split('+')[0],
                    "%Y-%m-%dT%H:%M:%S"
                ).replace(tzinfo=timezone.utc)
            except:
                return None

    def _calculate_age_days(self, published_at: str) -> float:
        """Calcula edad en días desde publicación."""
        dt = self._parse_datetime(published_at)
        if not dt:
            return 365  # Default 1 año si falla parsing
        
        now = datetime.now(timezone.utc)
        delta = now - dt
        return max(delta.days, 1)  # Mínimo 1 día