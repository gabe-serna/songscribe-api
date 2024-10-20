import logging
import os
import re
import string
from typing import List

from loguru import logger as log
import yt_dlp
from pytube import Search

# Configure logging
logger = logging.getLogger("pytube")
logger.setLevel(logging.ERROR)

def _sanitize_filename(filename):
    safe_chars = "-_.() %s%s" % (
        re.escape(string.ascii_letters),
        re.escape(string.digits),
    )
    safe_filename = re.sub(f"[^{safe_chars}]", "_", filename)
    return safe_filename.strip()

def download_audio_from_youtube(url, output_path):
    """
    Downloads audio from a YouTube URL and saves it as an MP3 file.

    Args:
        url (str): The YouTube video URL.
        output_path (str): The directory where the audio file will be saved.

    Returns:
        str: The filename of the downloaded MP3 file.

    Raises:
        ValueError: If the video duration exceeds 6 minutes.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info_dict = ydl.extract_info(url, download=False)

    if info_dict.get("duration", 0) > 360:
        raise ValueError("Song is too long. Please use a song no longer than 6 minutes.")

    video_title = info_dict.get("title", None)
    video_title = _sanitize_filename(video_title)

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": os.path.join(output_path, video_title),
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return f"{video_title}.mp3"

def query_youtube(query: str) -> Search:
    """
    Performs a YouTube search using the provided query.

    Args:
        query (str): The search query.

    Returns:
        Search: A pytube Search object containing the search results.
    """
    return Search(query)

def search_youtube(query: str, limit=5) -> (List[str], List):
    """
    Searches YouTube for videos matching the query and returns video titles and results.

    Args:
        query (str): The search query.
        limit (int): The maximum number of results to return.

    Returns:
        Tuple[List[str], List]: A tuple containing a list of video titles and a list of video results.
    """
    log.info(f"Searching YouTube for query: {query}")

    if len(query) > 3:
        search = query_youtube(query + " lyrics")
        search_results = search.results[:limit] if search.results else []
        video_options = [video.title for video in search_results]
    else:
        video_options = []
        search_results = []

    return video_options, search_results

def get_youtube_url(title: str, video_options: List[str], search_results: List) -> str:
    """
    Retrieves the YouTube URL for a video title from the search results.

    Args:
        title (str): The title of the video.
        video_options (List[str]): A list of video titles.
        search_results (List): A list of video results.

    Returns:
        str: The YouTube video URL.

    Raises:
        ValueError: If the title is not found in the video options.
    """
    try:
        index = video_options.index(title)
    except ValueError:
        raise ValueError("Title not found in video options.")
    video = search_results[index]
    return video.watch_url

def check_if_is_youtube_url(url: str) -> bool:
    """
    Checks if a given string is a valid YouTube URL.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if it's a YouTube URL, False otherwise.
    """
    return url.startswith("http")
