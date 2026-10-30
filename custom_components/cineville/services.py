"""The integration's actions: about one film, seen or not, and its trailer on a media player."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import CONF_PLAYER, DATA_SEEN, DOMAIN
from .coordinator import setting
from .films import Film
from .seen import SeenFilms

ATTR_FILM = "film"
FILM_SCHEMA = vol.Schema({vol.Required(ATTR_FILM): cv.string})
PLAY_SCHEMA = vol.Schema({vol.Required(ATTR_FILM): cv.string, vol.Optional(ATTR_ENTITY_ID): cv.entity_id})


def _entries(hass: HomeAssistant):
    return [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]


def find_film(hass: HomeAssistant, film: str) -> tuple[Film | None, Any]:
    """A film by its id or title in any city set up, with the config entry that knows it."""
    for entry in _entries(hass):
        data = entry.runtime_data.data
        if data and (found := data.find(film)):
            return found, entry
    return None, None


def default_player(hass: HomeAssistant, entry) -> str | None:
    """The media player the trailers play on: the one of the film's city, else of any city."""
    for e in [entry, *_entries(hass)]:
        if e is not None and (player := setting(e, CONF_PLAYER, None)):
            return player
    return None


def player_name(hass: HomeAssistant, entity_id: str | None) -> str:
    if not entity_id:
        return ""
    state = hass.states.get(entity_id)
    return (state.name if state else entity_id) or entity_id


def media_id(film: Film) -> str:
    return f"media-source://{DOMAIN}/{film.id}"


def async_register(hass: HomeAssistant) -> None:
    seen: SeenFilms = hass.data[DATA_SEEN]

    def need(film_text: str) -> tuple[Film, Any]:
        film, entry = find_film(hass, film_text)
        if film is None:
            raise ServiceValidationError(f"Cineville does not show a film called {film_text!r} in your cities now")
        return film, entry

    async def get_film(call: ServiceCall) -> ServiceResponse:
        film, entry = need(call.data[ATTR_FILM])
        player = default_player(hass, entry)
        return film.answer(dt_util.get_default_time_zone(), seen.is_seen(film.id, film.title),
                           player_name(hass, player) if film.trailer else "")

    async def mark_seen(call: ServiceCall) -> None:
        film, _ = find_film(hass, call.data[ATTR_FILM])
        if film is not None:
            seen.add(film.id, film.title)
        else:
            seen.add(None, call.data[ATTR_FILM].strip())

    async def unmark_seen(call: ServiceCall) -> None:
        film, _ = find_film(hass, call.data[ATTR_FILM])
        seen.remove(film.id if film else call.data[ATTR_FILM], film.title if film else call.data[ATTR_FILM])

    async def play_trailer(call: ServiceCall) -> None:
        film, entry = need(call.data[ATTR_FILM])
        if not film.trailer:
            raise ServiceValidationError(f"{film.title} has no trailer at Cineville")
        player = call.data.get(ATTR_ENTITY_ID) or default_player(hass, entry)
        if not player:
            raise ServiceValidationError("Choose a media player in the Cineville options, or name one")
        await hass.services.async_call("media_player", "play_media", {
            ATTR_ENTITY_ID: player,
            "media_content_id": media_id(film),
            "media_content_type": "video/mp4",
        }, blocking=True)

    hass.services.async_register(DOMAIN, "get_film", get_film, FILM_SCHEMA, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "mark_seen", mark_seen, FILM_SCHEMA)
    hass.services.async_register(DOMAIN, "unmark_seen", unmark_seen, FILM_SCHEMA)
    hass.services.async_register(DOMAIN, "play_trailer", play_trailer, PLAY_SCHEMA)
