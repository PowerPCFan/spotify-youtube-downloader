# ruff: noqa: PLR0913, PLR0917

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any, NotRequired, Self, TypedDict

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
