# ruff: noqa: PLR0913, PLR0917

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, NotRequired, Self, TypedDict

import dotenv
import googleapiclient.discovery
import yt_dlp
from discord import Intents, Message, TextChannel
from discord.ext import commands
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

if TYPE_CHECKING:
    from collections.abc import Mapping


class SpotifyObjectType(StrEnum):
    ALBUM = "album"
    ARTIST = "artist"
    TRACK = "track"
    PLAYLIST = "playlist"

    @classmethod
    def from_str(cls, value: str) -> Self:
        return cls(value)


class ReleaseDatePrecision(StrEnum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"

    @classmethod
    def from_str(cls, value: str) -> Self:
        return cls(value)


class CurrentlyPlayingType(StrEnum):
    TRACK = "track"
    EPISODE = "episode"
    AD = "ad"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> Self:
        return cls(value)


class ExternalUrlsDict(TypedDict):
    spotify: str


class ImageDict(TypedDict):
    height: int
    url: str
    width: int


class ArtistDict(TypedDict):
    external_urls: ExternalUrlsDict
    href: str
    id: str
    name: str
    type: str
    uri: str


class AlbumDict(TypedDict):
    album_type: str
    artists: list[ArtistDict]
    external_urls: ExternalUrlsDict
    href: str
    id: str
    images: list[ImageDict]
    name: str
    release_date: str
    release_date_precision: str
    total_tracks: int
    type: str
    uri: str


class TrackDict(TypedDict):
    album: AlbumDict
    artists: list[ArtistDict]
    disc_number: int
    duration_ms: int
    explicit: bool
    external_urls: ExternalUrlsDict
    href: str
    id: str
    is_local: bool
    name: str
    preview_url: str | None
    track_number: int
    type: str
    uri: str


class ContextDict(TypedDict):
    external_urls: ExternalUrlsDict
    href: str
    type: str
    uri: str


class DisallowsDict(TypedDict):
    resuming: NotRequired[bool]
    pausing: NotRequired[bool]
    skipping_next: NotRequired[bool]
    skipping_prev: NotRequired[bool]
    seeking: NotRequired[bool]


class ActionsDict(TypedDict):
    disallows: DisallowsDict


class SeenSpotifyTrackDict(TypedDict):
    is_playing: bool
    timestamp: int
    context: ContextDict
    progress_ms: int
    item: TrackDict
    currently_playing_type: str
    actions: ActionsDict


class ExternalUrls:
    def __init__(self, spotify: str) -> None:
        self.spotify = spotify

    @classmethod
    def from_dict(cls, data: ExternalUrlsDict) -> Self:
        return cls(spotify=data["spotify"])


class SpotifyImage:
    def __init__(self, height: int, url: str, width: int) -> None:
        self.height = height
        self.url = url
        self.width = width

    @classmethod
    def from_dict(cls, data: ImageDict) -> Self:
        return cls(
            height=data["height"],
            url=data["url"],
            width=data["width"],
        )


class SpotifyArtist:
    def __init__(
        self,
        external_urls: ExternalUrls,
        href: str,
        id: str,
        name: str,
        type: SpotifyObjectType,
        uri: str,
    ) -> None:
        self.external_urls = external_urls
        self.href = href
        self.id = id
        self.name = name
        self.type = type
        self.uri = uri

    @classmethod
    def from_dict(cls, data: ArtistDict) -> Self:
        return cls(
            external_urls=ExternalUrls.from_dict(data["external_urls"]),
            href=data["href"],
            id=data["id"],
            name=data["name"],
            type=SpotifyObjectType.from_str(data["type"]),
            uri=data["uri"],
        )


class SpotifyAlbum:
    def __init__(
        self,
        album_type: str,
        artists: list[SpotifyArtist],
        external_urls: ExternalUrls,
        href: str,
        id: str,
        images: list[SpotifyImage],
        name: str,
        release_date: str,
        release_date_precision: ReleaseDatePrecision,
        total_tracks: int,
        type: SpotifyObjectType,
        uri: str,
    ) -> None:
        self.album_type = album_type
        self.artists = artists
        self.external_urls = external_urls
        self.href = href
        self.id = id
        self.images = images
        self.name = name
        self.release_date = release_date
        self.release_date_precision = release_date_precision
        self.total_tracks = total_tracks
        self.type = type
        self.uri = uri

    @classmethod
    def from_dict(cls, data: AlbumDict) -> Self:
        return cls(
            album_type=data["album_type"],
            artists=[SpotifyArtist.from_dict(a) for a in data["artists"]],
            external_urls=ExternalUrls.from_dict(data["external_urls"]),
            href=data["href"],
            id=data["id"],
            images=[SpotifyImage.from_dict(i) for i in data["images"]],
            name=data["name"],
            release_date=data["release_date"],
            release_date_precision=ReleaseDatePrecision.from_str(
                data["release_date_precision"],
            ),
            total_tracks=data["total_tracks"],
            type=SpotifyObjectType.from_str(data["type"]),
            uri=data["uri"],
        )


class SpotifyTrack:
    def __init__(
        self,
        album: SpotifyAlbum,
        artists: list[SpotifyArtist],
        disc_number: int,
        duration_ms: int,
        explicit: bool,
        external_urls: ExternalUrls,
        href: str,
        id: str,
        is_local: bool,
        name: str,
        preview_url: str | None,
        track_number: int,
        type: SpotifyObjectType,
        uri: str,
    ) -> None:
        self.album = album
        self.artists = artists
        self.disc_number = disc_number
        self.duration_ms = duration_ms
        self.explicit = explicit
        self.external_urls = external_urls
        self.href = href
        self.id = id
        self.is_local = is_local
        self.name = name
        self.preview_url = preview_url
        self.track_number = track_number
        self.type = type
        self.uri = uri

    @classmethod
    def from_dict(cls, data: TrackDict) -> Self:
        return cls(
            album=SpotifyAlbum.from_dict(data["album"]),
            artists=[SpotifyArtist.from_dict(a) for a in data["artists"]],
            disc_number=data["disc_number"],
            duration_ms=data["duration_ms"],
            explicit=data["explicit"],
            external_urls=ExternalUrls.from_dict(data["external_urls"]),
            href=data["href"],
            id=data["id"],
            is_local=data["is_local"],
            name=data["name"],
            preview_url=data["preview_url"],
            track_number=data["track_number"],
            type=SpotifyObjectType.from_str(data["type"]),
            uri=data["uri"],
        )


class SpotifyContext:
    def __init__(
        self,
        external_urls: ExternalUrls,
        href: str,
        type: SpotifyObjectType,
        uri: str,
    ) -> None:
        self.external_urls = external_urls
        self.href = href
        self.type = type
        self.uri = uri

    @classmethod
    def from_dict(cls, data: ContextDict) -> Self:
        return cls(
            external_urls=ExternalUrls.from_dict(data["external_urls"]),
            href=data["href"],
            type=SpotifyObjectType.from_str(data["type"]),
            uri=data["uri"],
        )


class SpotifyDisallows:
    def __init__(
        self,
        resuming: bool = False,
        pausing: bool = False,
        skipping_next: bool = False,
        skipping_prev: bool = False,
        seeking: bool = False,
    ) -> None:
        self.resuming = resuming
        self.pausing = pausing
        self.skipping_next = skipping_next
        self.skipping_prev = skipping_prev
        self.seeking = seeking

    @classmethod
    def from_dict(cls, data: DisallowsDict) -> Self:
        return cls(
            resuming=data.get("resuming", False),
            pausing=data.get("pausing", False),
            skipping_next=data.get("skipping_next", False),
            skipping_prev=data.get("skipping_prev", False),
            seeking=data.get("seeking", False),
        )


class SpotifyActions:
    def __init__(self, disallows: SpotifyDisallows) -> None:
        self.disallows = disallows

    @classmethod
    def from_dict(cls, data: ActionsDict) -> Self:
        return cls(disallows=SpotifyDisallows.from_dict(data["disallows"]))


class SeenSpotifyTrack:
    def __new__(cls, data: Mapping[str, Any]) -> Self:
        self = super().__new__(cls)
        self.is_playing = data["is_playing"]
        self.timestamp = data["timestamp"]
        ctx = data.get("context")
        self.context = SpotifyContext.from_dict(ctx) if ctx is not None else None
        self.progress_ms = data["progress_ms"]
        self.item = SpotifyTrack.from_dict(data["item"])
        self.currently_playing_type = CurrentlyPlayingType.from_str(
            data["currently_playing_type"],
        )
        self.actions = SpotifyActions.from_dict(data["actions"])
        return self

    is_playing: bool
    timestamp: int
    context: SpotifyContext | None
    progress_ms: int
    item: SpotifyTrack
    currently_playing_type: CurrentlyPlayingType
    actions: SpotifyActions

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(data)


class DownloadsListItem:
    def __init__(self, name: str, artist: str, album: str, date: int) -> None:
        self.name = name
        self.artist = artist
        self.album = album
        self.date = date

    @classmethod
    def from_seen_spotify_track(cls, track: SeenSpotifyTrack) -> Self:
        return cls(
            name=track.item.name,
            artist=track.item.artists[0].name,
            album=track.item.album.name,
            date=int(time.time()),
        )

    def matches(self, track: SeenSpotifyTrack) -> bool:
        inst_itm = self
        track_itm = DownloadsListItem.from_seen_spotify_track(track)
        return (
            inst_itm.name == track_itm.name and
            inst_itm.artist == track_itm.artist and
            inst_itm.album == track_itm.album
        )


PARENT = Path(__file__).parent
ENV = PARENT / ".env"
CACHE = PARENT / "spotify-cache.json"
DOWNLOADS = PARENT / "downloads"
DOWNLOADS_LIST = PARENT / "downloaded.json"
if not DOWNLOADS_LIST.exists() or (DOWNLOADS_LIST.exists() and not DOWNLOADS_LIST.read_text().strip()):
    DOWNLOADS_LIST.write_text("[]")  # ensure its a list

dotenv.load_dotenv(dotenv_path=ENV)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SPOTIFY_ID = os.getenv("SPOTIFY_ID")
SPOTIFY_SECRET = os.getenv("SPOTIFY_SECRET")
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
SERVER_ID = os.getenv("DISCORD_SERVER_ID", "")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
PING = os.getenv("DISCORD_PING", "")

bot = commands.Bot(command_prefix=".", intents=Intents.all())

pending_downloads: dict[int, dict[str, Any]] = {}
pending_lock = threading.Lock()


@bot.event
async def on_ready() -> None:  # noqa: RUF029
    print(f"Bot logged in as {bot.user}")


@bot.event
async def on_message(message: Message) -> None:
    if message.author == bot.user:
        return

    server_obj = bot.get_guild(int(SERVER_ID))
    channel_obj: TextChannel = server_obj.get_channel(int(CHANNEL_ID))  # type: ignore  # noqa: PGH003

    if message.channel == channel_obj and message.reference and message.reference.message_id in pending_downloads:
        await handle_user_reply(message, message.reference.message_id)

    await bot.process_commands(message)


def send_download_options(
    track: SeenSpotifyTrack,
    results: list[dict[str, Any]],
) -> str | None:
    channel: TextChannel = bot.get_guild(int(SERVER_ID)).get_channel(int(CHANNEL_ID))  # type: ignore  # noqa: PGH003

    prompt = f"{PING} Found {len(results)} matches for *{track.item.name}* by {track.item.artists[0].name}:\n\n"
    for i, result in enumerate(results, 1):
        title = result["title"]
        title = title[:100] if len(title) > 100 else title  # noqa: PLR2004
        prompt += f"{i}. [{title}](<{result["url"]}>)\n"
    prompt += "Reply with the best option:"

    selected_url_ref: list[str | None] = [None]
    message_id: int | None = None

    async def send_and_track() -> None:
        nonlocal message_id
        msg = await channel.send(prompt)
        message_id = msg.id
        with pending_lock:
            pending_downloads[message_id] = {
                "track": track,
                "results": results,
                "channel": channel,
                "selected_url_ref": selected_url_ref,
            }

    try:
        asyncio.run_coroutine_threadsafe(send_and_track(), bot.loop)
    except Exception as e:
        print(f"Error sending download options: {e}")
        return None

    timeout = 60 * 15
    start_time = time.time()

    while selected_url_ref[0] is None:
        time.sleep(1)
        if time.time() - start_time > timeout:
            print("Timeout waiting for user selection")
            with pending_lock:
                to_remove = [
                    mid for mid, data in pending_downloads.items()
                    if data["track"] is track
                ]
                for mid in to_remove:
                    del pending_downloads[mid]
            return None

    selected = selected_url_ref[0]
    with pending_lock:
        if message_id is not None and message_id in pending_downloads:
            del pending_downloads[message_id]
    return selected


async def handle_user_reply(message: Message, prompt_message_id: int) -> None:
    with pending_lock:
        if prompt_message_id not in pending_downloads:
            return

        data = pending_downloads.pop(prompt_message_id)
        results = data["results"]
        selected_url_ref = data["selected_url_ref"]

    try:  # noqa: PLW0717
        choice = int(message.content.strip())
        if 1 <= choice <= len(results):
            selected = results[choice - 1]
            print(f"[{time.strftime('%H:%M:%S')}] User selected: {selected['title']}")
            selected_url_ref[0] = selected["url"]
            # Acknowledge the selection
            await message.reply(f"Selected *{selected['title']}*, download starting!")
        else:
            await message.reply("Invalid choice. Please reply with a number between 1 and 10.")
            selected_url_ref[0] = None
            with pending_lock:
                pending_downloads[prompt_message_id] = data
    except ValueError:
        await message.reply("Invalid input. Please reply with a number.")
        selected_url_ref[0] = None
        with pending_lock:
            pending_downloads[prompt_message_id] = data


def run_bot() -> None:
    bot.run(TOKEN)


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
    return f"{track.item.name} {", ".join(a.name for a in artists)} song"


def search_youtube(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    try:
        request = youtube.search().list(
            q=query,
            part="id,snippet",
            type="video",
            maxResults=max_results,
        )
        response = request.execute()

        return [
            {
                "id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
            }
            for item in response.get("items", [])
        ]
    except Exception as e:
        print(f"[ERROR] YouTube search failed: {e}")
        return []


pending_selection_queue: list[tuple[SeenSpotifyTrack, str]] = []
pending_selection_lock = threading.Lock()
pending_selection_event = threading.Event()

download_queue: list[tuple[SeenSpotifyTrack, str]] = []
download_lock = threading.Lock()
download_event = threading.Event()
in_flight_track_ids: set[str] = set()


def get_downloads_list() -> list[DownloadsListItem]:
    try:
        return [DownloadsListItem(**item) for item in json.loads(DOWNLOADS_LIST.read_text())]
    except Exception as e:
        print(f"Error loading downloads list: {e}")
    return []


def save_to_downloaded_json(track: SeenSpotifyTrack) -> None:
    with DOWNLOADS_LIST.open("r") as f:
        data: list[dict[str, str | int]] = json.load(f)

    for item in data:
        if (
            f"{item['name']}_{item['artist']}_{item['album']}".lower().strip() ==
            f"{track.item.name}_{track.item.artists[0].name}_{track.item.album.name}".lower().strip()
        ):
            return

    data.append({
        "name": track.item.name,
        "artist": track.item.artists[0].name,
        "album": track.item.album.name,
        "date": int(time.time()),
    })

    with DOWNLOADS_LIST.open("w") as f:
        json.dump(data, f, indent=4)


def download_track(track: SeenSpotifyTrack, youtube_url: str) -> bool:
    print(f"[{time.strftime('%H:%M:%S')}] Downloading: {track.item.name} by {track.item.artists[0].name}")
    yt_dlp.YoutubeDL({
        "outtmpl": str(DOWNLOADS.resolve() / "%(title)s.%(ext)s"),
        "format": "bestaudio[ext=opus]/bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "opus",
        }],
    }).download([youtube_url])
    print(f"[{time.strftime('%H:%M:%S')}] Downloaded: {track.item.name} by {track.item.artists[0].name}")
    return True


def pending_selection_worker() -> None:
    while True:
        pending_selection_event.wait()
        pending_selection_event.clear()

        with pending_selection_lock:
            if not pending_selection_queue:
                continue
            track, youtube_query = pending_selection_queue.pop(0)

        if any(item.matches(track) for item in get_downloads_list()):
            print(f"[{time.strftime('%H:%M:%S')}] Skipping already downloaded: {track.item.name}")
            with download_lock:
                seen_tracks[:] = [(t, q) for t, q in seen_tracks if t is not track]
                in_flight_track_ids.discard(track.item.id)
            continue

        print(f"[{time.strftime('%H:%M:%S')}] Searching YouTube for: {youtube_query}")
        results = search_youtube(youtube_query, max_results=10)
        if not results:
            print(f"[{time.strftime('%H:%M:%S')}] No YouTube results found for: {track.item.name}")
            with download_lock:
                seen_tracks[:] = [(t, q) for t, q in seen_tracks if t is not track]
                in_flight_track_ids.discard(track.item.id)
            continue

        print(f"[{time.strftime('%H:%M:%S')}] Sending Discord message with {len(results)} options...")
        selected_url = send_download_options(track, results)

        if selected_url is None:
            print(f"[{time.strftime('%H:%M:%S')}] No selection made for: {track.item.name}")
            with download_lock:
                seen_tracks[:] = [(t, q) for t, q in seen_tracks if t is not track]
                in_flight_track_ids.discard(track.item.id)
            continue

        print(f"[{time.strftime('%H:%M:%S')}] User selected: {selected_url}")

        with download_lock:
            download_queue.append((track, selected_url))
            download_event.set()

        with download_lock:
            seen_tracks[:] = [(t, q) for t, q in seen_tracks if t is not track]
            in_flight_track_ids.discard(track.item.id)


def download_worker() -> None:
    while True:
        download_event.wait()
        download_event.clear()

        with download_lock:
            if not download_queue:
                continue
            track, youtube_url = download_queue.pop(0)

        success = download_track(track, youtube_url)

        if success:
            save_to_downloaded_json(track)
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to download: {track.item.name}")


def queue_download(track: SeenSpotifyTrack, youtube_query: str) -> None:
    with pending_selection_lock:
        pending_selection_queue.append((track, youtube_query))
    pending_selection_event.set()


print("Starting Discord bot...")
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

while not bot.is_ready():
    time.sleep(0.5)

download_thread = threading.Thread(target=download_worker, daemon=True)
download_thread.start()

pending_thread = threading.Thread(target=pending_selection_worker, daemon=True)
pending_thread.start()

seen_tracks: list[tuple[SeenSpotifyTrack, str]] = []

last_seen_track_id: str | None = None


while True:
    print()

    try:
        raw = spotify.current_user_playing_track()
    except Exception as e:
        print(f"[ERROR] Failed to fetch currently playing track: {e}")
        time.sleep(30)
        continue

    if not raw:
        intr = 30
        print(f"No track currently playing. Checking again in {intr}s...")
        last_seen_track_id = None
        time.sleep(intr)
        continue

    track = SeenSpotifyTrack.from_dict(raw)

    with download_lock:
        already_in_flight = track.item.id in in_flight_track_ids

    if track.item.id == last_seen_track_id or already_in_flight:
        print(
            f"[{time.strftime('%H:%M:%S')}] Skipping (already in flight or unchanged): "
            f"{track.item.name} by {track.item.artists[0].name}",
        )
        time.sleep(15)
        continue

    last_seen_track_id = track.item.id
    youtube_query = make_youtube_query(track)
    with download_lock:
        seen_tracks.append((track, youtube_query))
        in_flight_track_ids.add(track.item.id)

    queue_download(track, youtube_query)

    print(
        f"[{time.strftime('%H:%M:%S')}] Currently playing: {track.item.name} by {track.item.artists[0].name} "
        f"on {track.item.album.name} ({track.item.external_urls.spotify})",
    )

    time.sleep(15)
