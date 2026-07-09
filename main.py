# ruff: noqa: PLR0913, PLR0917, C901, PLR0914, PLR0915, PLW0717, PLR2004, RUF029, PGH003

from __future__ import annotations

import asyncio
import html
import json
import os
import re
import threading
import time
import traceback
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


class DownloadJob(TypedDict):
    youtube_url: str
    display_name: str
    track: SeenSpotifyTrack | None


@bot.event
async def on_ready() -> None:
    print(f"Bot logged in as {bot.user}")


@bot.event
async def on_message(message: Message) -> None:
    if message.author == bot.user:
        return

    if message.reference and message.reference.message_id in pending_downloads:
        await handle_user_reply(message, message.reference.message_id)

    await bot.process_commands(message)


def get_default_channel() -> TextChannel | None:
    try:
        guild = bot.get_guild(int(SERVER_ID))
        if guild is None:
            return None
        channel = guild.get_channel(int(CHANNEL_ID))
        return channel if isinstance(channel, TextChannel) else None
    except Exception:
        return None


def is_youtube_url(value: str) -> bool:
    return "youtube.com/watch?v=" in value or "youtu.be/" in value


def build_download_picker_prompt(
    intro_line: str,
    results: list[dict[str, Any]],
    spotify_duration_ms: int | None = None,
) -> str:
    prompt = f"{intro_line}\n\n"
    for i, result in enumerate(results, 1):
        title = html.unescape(result["title"])
        title = title[:100] if len(title) > 100 else title
        channel_name = result["channel"]
        channel_info = result.get("channel_info")
        duration_ms = result.get("duration_ms")

        channel_line = f"   - Channel: {channel_name}"
        if channel_info:
            subs = format_subscribers(channel_info["subscriber_count"])
            channel_line += f" ({subs} Subscribers)"

        duration_line = ""
        if duration_ms is not None:
            yt_duration = format_duration(duration_ms)
            if spotify_duration_ms is None:
                duration_line = f"\n   - Song Length: {yt_duration}"
            else:
                diff_ms = duration_ms - spotify_duration_ms
                if diff_ms > 0:
                    diff_formatted = format_duration(diff_ms)
                    duration_line = f"\n   - Song Length: {yt_duration} (+{diff_formatted} longer than Spotify)"
                elif diff_ms < 0:
                    diff_formatted = format_duration(abs(diff_ms))
                    duration_line = f"\n   - Song Length: {yt_duration} (-{diff_formatted} shorter than Spotify)"
                else:
                    duration_line = f"\n   - Song Length: {yt_duration} (Same length as Spotify)"

        prompt += f"{i}. [{title}](<{result['url']}>)\n{channel_line}{duration_line}\n"
    prompt += "Reply with the best option or a YouTube URL:"
    return prompt


def send_picker_and_wait(
    channel: TextChannel,
    prompt: str,
    results: list[dict[str, Any]],
) -> str | None:
    selected_url_ref: list[str | None] = [None]
    message_id: int | None = None

    async def send_and_track() -> None:
        nonlocal message_id
        try:
            msg = await asyncio.wait_for(channel.send(prompt), timeout=10.0)
            message_id = msg.id
            with pending_lock:
                pending_downloads[message_id] = {
                    "results": results,
                    "channel": channel,
                    "selected_url_ref": selected_url_ref,
                }
        except TimeoutError:
            print("[ERROR] Message send timed out after 10 seconds")
        except Exception as e:
            print(f"[ERROR] Error sending message: {e}")
            traceback.print_exc()

    try:
        asyncio.run_coroutine_threadsafe(send_and_track(), bot.loop)
    except Exception as e:
        print(f"[ERROR] Error sending download options: {e}")
        traceback.print_exc()
        return None

    timeout = 60 * 15
    start_time = time.time()

    while selected_url_ref[0] is None:
        time.sleep(1)
        if time.time() - start_time > timeout:
            print("Timeout waiting for user selection")
            with pending_lock:
                if message_id is not None and message_id in pending_downloads:
                    del pending_downloads[message_id]
            return None

    selected = selected_url_ref[0]
    with pending_lock:
        if message_id is not None and message_id in pending_downloads:
            del pending_downloads[message_id]
    return selected


def send_download_options(
    track: SeenSpotifyTrack,
    results: list[dict[str, Any]],
) -> str | None:
    channel = get_default_channel()
    if channel is None:
        return None

    spotify_duration = format_duration(track.item.duration_ms)
    intro = (
        f"{PING} Found {len(results)} matches for *{track.item.name}* by "
        f"{track.item.artists[0].name} (Spotify: {spotify_duration}):"
    )
    prompt = build_download_picker_prompt(
        intro,
        results,
        spotify_duration_ms=track.item.duration_ms,
    )
    return send_picker_and_wait(channel, prompt, results)


def queue_download_job(
    youtube_url: str,
    display_name: str,
    track: SeenSpotifyTrack | None = None,
) -> None:
    with download_lock:
        download_queue.append({
            "youtube_url": youtube_url,
            "display_name": display_name,
            "track": track,
        })
        download_event.set()


async def handle_user_reply(message: Message, prompt_message_id: int) -> None:
    with pending_lock:
        if prompt_message_id not in pending_downloads:
            return

        data = pending_downloads.pop(prompt_message_id)
        results = data["results"]
        selected_url_ref = data["selected_url_ref"]

    try:
        choice = int(message.content.strip())
        if 1 <= choice <= len(results):
            selected = results[choice - 1]
            print(f"[{time.strftime('%H:%M:%S')}] User selected: {selected['title']}")
            selected_url_ref[0] = selected["url"]
            # Acknowledge the selection
            await message.reply(f"Selected *{selected['title']}*, download starting!")
        else:
            await message.reply("Invalid choice. Please reply with a number between 1 and 8, or paste a YouTube URL.")
            selected_url_ref[0] = None
            with pending_lock:
                pending_downloads[prompt_message_id] = data
    except ValueError:
        url = message.content.strip()
        if is_youtube_url(url):
            print(f"[{time.strftime('%H:%M:%S')}] User selected custom URL: {url}")
            selected_url_ref[0] = url
            await message.reply("Selected custom URL, download starting!")
        else:
            await message.reply("Invalid input. Please reply with the number of the item you'd like to select, or paste a YouTube URL.")  # noqa: E501
            selected_url_ref[0] = None
            with pending_lock:
                pending_downloads[prompt_message_id] = data


@bot.command(name="download")
async def download_command(ctx: commands.Context[commands.Bot], *, query_or_url: str = "") -> None:
    query_or_url = query_or_url.strip()
    if not query_or_url:
        await ctx.reply("Usage: `.download <YouTube query or URL>`")
        return

    if is_youtube_url(query_or_url):
        queue_download_job(
            youtube_url=query_or_url,
            display_name=f"manual URL <{query_or_url}>",
            track=None,
        )
        await ctx.reply(f"Queued direct download from <{query_or_url}>.")
        return

    if not isinstance(ctx.channel, TextChannel):
        await ctx.reply("This command only works in a server text channel.")
        return

    await ctx.reply(f"Searching YouTube for: *{query_or_url}*")
    results = await asyncio.to_thread(search_youtube, query_or_url, 8)
    if not results:
        await ctx.reply("No YouTube results found for that query.")
        return

    intro = f"{PING} Found {len(results)} matches for *{query_or_url}*:"
    prompt = build_download_picker_prompt(intro, results)
    selected_url = await asyncio.to_thread(send_picker_and_wait, ctx.channel, prompt, results)
    if selected_url is None:
        await ctx.reply("No selection was made in time.")
        return

    selected_result = next((item for item in results if item["url"] == selected_url), None)
    display_name = (
        f"*{html.unescape(selected_result['title'])}*"
        if selected_result is not None
        else f"manual query: *{query_or_url}*"
    )
    queue_download_job(
        youtube_url=selected_url,
        display_name=display_name,
        track=None,
    )


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
    artists = track.item.artists[:3] if len(track.item.artists) > 3 else track.item.artists
    return f"{track.item.name} {', '.join(a.name for a in artists)} song"


def format_subscribers(count: int) -> str:
    if count >= 1_000_000:
        millions = count / 1_000_000
        if millions >= 100:
            return f"{int(millions)}M"
        return f"{millions:.2f}M"
    elif count >= 1_000:
        thousands = count / 1_000
        if thousands >= 100:
            return f"{int(thousands)}K"
        return f"{thousands:.2f}K"
    return str(count)


def format_duration(ms: int) -> str:
    total_seconds = ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


def search_youtube(query: str, max_results: int) -> list[dict[str, Any]]:
    try:
        request = youtube.search().list(
            q=query,
            part="id,snippet",
            type="video",
            maxResults=max_results,
        )
        response = request.execute()

        channel_ids = list({item["snippet"]["channelId"] for item in response.get("items", [])})

        channel_info = {}
        if channel_ids:
            channel_request = youtube.channels().list(
                part="snippet,statistics",
                id=",".join(channel_ids),
            )
            channel_response = channel_request.execute()
            for channel in channel_response.get("items", []):
                channel_info[channel["id"]] = {
                    "title": channel["snippet"]["title"],
                    "subscriber_count": int(channel["statistics"].get("subscriberCount", "0")),
                }

        video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
        video_duration_info = {}
        if video_ids:
            video_request = youtube.videos().list(
                part="contentDetails",
                id=",".join(video_ids),
            )
            video_response = video_request.execute()
            for video in video_response.get("items", []):
                duration_str = video["contentDetails"]["duration"]
                pattern = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
                match = pattern.match(duration_str)
                if match:
                    hours = int(match.group(1) or 0)
                    minutes = int(match.group(2) or 0)
                    seconds = int(match.group(3) or 0)
                    total_ms = ((hours * 60 + minutes) * 60 + seconds) * 1000
                    video_duration_info[video["id"]] = total_ms

        return [
            {
                "id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "channel_id": item["snippet"]["channelId"],
                "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
                "channel_info": channel_info.get(item["snippet"]["channelId"]),
                "duration_ms": video_duration_info.get(item["id"]["videoId"]),
            }
            for item in response.get("items", [])
        ]
    except Exception as e:
        print(f"[ERROR] YouTube search failed: {e}")
        return []


pending_selection_queue: list[tuple[SeenSpotifyTrack, str]] = []
pending_selection_lock = threading.Lock()
pending_selection_event = threading.Event()

download_queue: list[DownloadJob] = []
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


def download_track(youtube_url: str, display_name: str, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Downloading: {display_name}")
            yt_dlp.YoutubeDL({
                "outtmpl": str(DOWNLOADS.resolve() / "%(title)s.%(ext)s"),
                "format": "bestaudio[ext=opus]/bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "opus",
                }],
            }).download([youtube_url])
            print(f"[{time.strftime('%H:%M:%S')}] Downloaded: {display_name}")
            return True
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:  # noqa: SIM102
                if attempt < max_retries - 1:
                    print(f"[{time.strftime('%H:%M:%S')}] 403 Forbidden error, retrying in 60 seconds (attempt {attempt + 1}/{max_retries})")  # noqa: E501
                    time.sleep(60)
                    continue
            break
    return False


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
        results = search_youtube(youtube_query, max_results=8)
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

        queue_download_job(
            youtube_url=selected_url,
            display_name=f"*{track.item.name}* by {track.item.artists[0].name}",
            track=track,
        )

        with download_lock:
            seen_tracks[:] = [(t, q) for t, q in seen_tracks if t is not track]
            in_flight_track_ids.discard(track.item.id)


async def send_download_status(channel: TextChannel, message: str) -> None:
    try:
        await channel.send(message)
    except Exception as e:
        print(f"[ERROR] Failed to send status message: {e}")


def download_worker() -> None:
    while True:
        try:
            download_event.wait()
            download_event.clear()

            with download_lock:
                if not download_queue:
                    continue
                job = download_queue.pop(0)

            youtube_url = job["youtube_url"]
            display_name = job["display_name"]
            track = job["track"]

            channel = get_default_channel()

            if channel:
                asyncio.run_coroutine_threadsafe(
                    send_download_status(channel, f"⬇️ Downloading {display_name}..."),
                    bot.loop,
                )

            success = download_track(youtube_url, display_name)

            if channel:
                if success:
                    if track is not None:
                        save_to_downloaded_json(track)
                    asyncio.run_coroutine_threadsafe(
                        send_download_status(channel, f"✅ Downloaded {display_name}!"),
                        bot.loop,
                    )
                else:
                    asyncio.run_coroutine_threadsafe(
                        send_download_status(channel, f"❌ Failed to download {display_name}"),
                        bot.loop,
                    )
            else:  # noqa: PLR5501
                if success:
                    if track is not None:
                        save_to_downloaded_json(track)
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Failed to download: {display_name}")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Download worker error: {e}")
            traceback.print_exc()
            time.sleep(1)


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
