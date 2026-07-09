import os
import time
from pathlib import Path

import dotenv
import googleapiclient.discovery

# import yt_dlp
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

from .models import SeenSpotifyTrack

PARENT = Path(__file__).parent
ENV = PARENT / ".env"
CACHE = PARENT / "spotify-cache.json"
DOWNLOADS = PARENT / "downloads"

dotenv.load_dotenv(dotenv_path=ENV)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SPOTIFY_ID = os.getenv("SPOTIFY_ID")
SPOTIFY_SECRET = os.getenv("SPOTIFY_SECRET")

spotify_oauth = SpotifyOAuth(
    client_id=SPOTIFY_ID,
    client_secret=SPOTIFY_SECRET,
    redirect_uri="http://127.0.0.1:8080/callback",
    scope=["user-read-currently-playing"],
    cache_path=CACHE,
)

spotify = Spotify(auth_manager=spotify_oauth)

youtube = googleapiclient.discovery.build(
    serviceName="youtube",
    version="v3",
    developerKey=YOUTUBE_API_KEY,
)


def make_youtube_query(track: SeenSpotifyTrack) -> str:
    artists = track.item.artists[:3] if len(track.item.artists) > 3 else track.item.artists  # noqa: PLR2004
    return f"{track.item.name} {artists}"


seen_tracks: list[tuple[SeenSpotifyTrack, str]] = []


while True:
    print()

    raw = spotify.current_user_playing_track()
    if not raw:
        print("No track currently playing. Checking again in 1 minute...")
        time.sleep(60)
        continue

    track = SeenSpotifyTrack.from_dict(raw)
    seen_tracks.append((track, make_youtube_query(track)))
    print(
        f"[{time.strftime('%H:%M:%S')}] Currently playing: {track.item.name} by {track.item.artists[0].name} "
        f"on {track.item.album.name} ({track.item.external_urls.spotify})",
    )

    time.sleep(15)
