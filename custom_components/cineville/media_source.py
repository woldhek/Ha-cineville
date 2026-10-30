"""The trailers in Home Assistant's media browser: Media → Cineville, and media-source://cineville/<film id> for any
media player that plays video."""

from __future__ import annotations

from homeassistant.components.media_player import BrowseError, MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .films import Film


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    return CinevilleMediaSource(hass)


def _films(hass: HomeAssistant) -> list[Film]:
    """Every film with a trailer in the cities set up, each once: now showing, then coming soon."""
    out: dict[str, Film] = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is not ConfigEntryState.LOADED or not entry.runtime_data.data:
            continue
        data = entry.runtime_data.data
        for film in [*data.now, *data.soon]:
            if film.trailer and film.id not in out:
                out[film.id] = film
    return list(out.values())


class CinevilleMediaSource(MediaSource):
    name = "Cineville"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        for film in _films(self.hass):
            if film.id == item.identifier:
                return PlayMedia(film.trailer, "video/mp4")
        raise Unresolvable(f"No Cineville trailer {item.identifier}")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        if item.identifier:
            raise BrowseError("A trailer has nothing to browse")
        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=film.id,
                media_class=MediaClass.VIDEO,
                media_content_type="video/mp4",
                title=film.title,
                can_play=True,
                can_expand=False,
                thumbnail=film.poster,
            )
            for film in _films(self.hass)
        ]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title="Cineville",
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=MediaClass.VIDEO,
        )
