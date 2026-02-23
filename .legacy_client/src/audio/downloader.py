"""
Audio Downloader Module

Downloads audio files from Stratus cloud storage (S3).
Handles caching to avoid re-downloading the same files.
"""

import os
import hashlib
import logging
import requests
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of an audio download operation."""
    success: bool
    file_path: Optional[Path] = None
    error: Optional[str] = None
    cached: bool = False
    size_bytes: int = 0


class AudioDownloader:
    """
    Downloads and caches audio files from URLs.
    
    Audio files are cached locally to avoid repeated downloads.
    Cache is stored in ~/.cache/StratusATC/audio/
    """
    
    DEFAULT_CACHE_DIR = "~/.cache/StratusATC/audio"
    REQUEST_TIMEOUT = 30  # seconds
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the audio downloader.
        
        Args:
            cache_dir: Custom cache directory. Defaults to ~/.cache/StratusATC/audio/
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir).expanduser()
        else:
            self.cache_dir = Path(self.DEFAULT_CACHE_DIR).expanduser()
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Audio cache directory: {self.cache_dir}")
    
    def _url_to_cache_key(self, url: str) -> str:
        """
        Convert a URL to a cache key (filename).
        
        Uses the last part of the URL path if it looks like a filename,
        otherwise falls back to a hash of the URL.
        """
        # Try to extract filename from URL
        # e.g., https://siaudio.s3.us-west-1.amazonaws.com/R26isgM5tKoFg82rSbTa.mp3
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path
            
            # Get the filename from path
            if path:
                filename = path.split('/')[-1]
                if filename and '.' in filename:
                    # Looks like a valid filename
                    return filename
        except Exception:
            pass
        
        # Fallback: hash the URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        return f"{url_hash}.mp3"
    
    def get_cached_path(self, url: str) -> Optional[Path]:
        """
        Check if a URL is already cached and return its path.
        
        Args:
            url: The audio URL to check
            
        Returns:
            Path to cached file if it exists, None otherwise
        """
        cache_key = self._url_to_cache_key(url)
        cache_path = self.cache_dir / cache_key
        
        if cache_path.exists() and cache_path.stat().st_size > 0:
            return cache_path
        return None
    
    def download(self, url: str, force: bool = False) -> DownloadResult:
        """
        Download an audio file from URL.
        
        Args:
            url: The URL to download from
            force: If True, re-download even if cached
            
        Returns:
            DownloadResult with file path or error
        """
        if not url:
            return DownloadResult(success=False, error="Empty URL provided")
        
        cache_key = self._url_to_cache_key(url)
        cache_path = self.cache_dir / cache_key
        
        # Check cache first (unless force download)
        if not force and cache_path.exists() and cache_path.stat().st_size > 0:
            logger.debug(f"Cache hit: {cache_key}")
            return DownloadResult(
                success=True,
                file_path=cache_path,
                cached=True,
                size_bytes=cache_path.stat().st_size
            )
        
        # Download the file
        logger.info(f"Downloading: {url}")
        try:
            response = requests.get(url, timeout=self.REQUEST_TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Get content length if available
            content_length = response.headers.get('content-length')
            if content_length:
                logger.debug(f"Content length: {content_length} bytes")
            
            # Write to cache file
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            size = cache_path.stat().st_size
            logger.info(f"Downloaded: {cache_key} ({size} bytes)")
            
            return DownloadResult(
                success=True,
                file_path=cache_path,
                cached=False,
                size_bytes=size
            )
            
        except requests.exceptions.Timeout:
            error = f"Download timeout after {self.REQUEST_TIMEOUT}s: {url}"
            logger.error(error)
            return DownloadResult(success=False, error=error)
            
        except requests.exceptions.HTTPError as e:
            error = f"HTTP error {e.response.status_code}: {url}"
            logger.error(error)
            return DownloadResult(success=False, error=error)
            
        except requests.exceptions.RequestException as e:
            error = f"Download failed: {e}"
            logger.error(error)
            return DownloadResult(success=False, error=error)
            
        except IOError as e:
            error = f"Failed to write cache file: {e}"
            logger.error(error)
            return DownloadResult(success=False, error=error)
    
    def clear_cache(self) -> Tuple[int, int]:
        """
        Clear all cached audio files.
        
        Returns:
            Tuple of (files_deleted, bytes_freed)
        """
        files_deleted = 0
        bytes_freed = 0
        
        for file_path in self.cache_dir.glob("*.mp3"):
            try:
                bytes_freed += file_path.stat().st_size
                file_path.unlink()
                files_deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}: {e}")
        
        logger.info(f"Cache cleared: {files_deleted} files, {bytes_freed} bytes")
        return files_deleted, bytes_freed
    
    def get_cache_stats(self) -> Tuple[int, int]:
        """
        Get cache statistics.
        
        Returns:
            Tuple of (file_count, total_bytes)
        """
        file_count = 0
        total_bytes = 0
        
        for file_path in self.cache_dir.glob("*.mp3"):
            file_count += 1
            total_bytes += file_path.stat().st_size
        
        return file_count, total_bytes
