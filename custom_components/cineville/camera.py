"""EXPERIMENTAL: a film's trailer as a camera, so a Tessera screen that streams (the ESP32-P4 boards) can play it
live on a tile, with its sound. Only with the option "Trailer camera (experimental)"; turn it off and this camera and
its select are gone again.

A Tessera screen cannot play an MP4: it shows a camera, which the Tessera app takes from Home Assistant's WebRTC
(its go2rtc) and sends on as pictures. So the trailer is this camera's stream source, played by go2rtc's ffmpeg at its
own speed (input=file), its video and sound as they are (copy; go2rtc makes the sound Opus for WebRTC itself). Until
it plays, and after, the camera's still is the film's poster."""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CinevilleConfigEntry
from .const import DOMAIN, WEBSITE
from .films import Film

_LOGGER = logging.getLogger(__name__)


def stream_source_of(trailer: str) -> str:
    """The trailer as go2rtc plays it: through ffmpeg, at the film's own speed, without transcoding."""
    return f"ffmpeg:{trailer}#input=file#video=copy#audio=copy"


async def async_setup_entry(hass: HomeAssistant, entry: CinevilleConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    camera = TrailerCamera(hass, entry)
    entry.runtime_data.trailer_camera = camera
    async_add_entities([camera])


class TrailerCamera(Camera):
    _attr_has_entity_name = True
    _attr_translation_key = "trailer"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, hass: HomeAssistant, entry: CinevilleConfigEntry) -> None:
        super().__init__()
        self._session = async_get_clientsession(hass)
        self._film: Film | None = None
        self._poster: tuple[str, bytes] | None = None
        self.on_change = None   # the select's, to follow the film the camera plays
        self._attr_unique_id = f"{entry.entry_id}_trailer"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Cineville",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=WEBSITE,
        )

    @property
    def film(self) -> Film | None:
        return self._film

    def set_film(self, film: Film | None) -> None:
        """The film whose trailer the camera plays from now on."""
        self._film = film if film and film.trailer else None
        self._attr_is_streaming = self._film is not None
        if self.hass:
            self.async_write_ha_state()
        if self.on_change:
            self.on_change()

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "cineville_trailer": True,
            "film_id": self._film.id if self._film else "",
            "film_title": self._film.title if self._film else "",
        }

    async def stream_source(self) -> str | None:
        return stream_source_of(self._film.trailer) if self._film and self._film.trailer else None

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """The film's poster, kept while the film is the same."""
        if not self._film or not self._film.poster:
            return None
        url = self._film.poster
        if self._poster and self._poster[0] == url:
            return self._poster[1]
        try:
            async with self._session.get(url, params={"w": str(width or 640), "fm": "jpg"},
                                         timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return None
                body = await response.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug("Poster of %s: %s", self._film.title, err)
            return None
        self._poster = (url, body)
        return body
