"""The films you have seen: one list for every city, kept in Home Assistant's storage.

A film is known by Cineville's own id, which stays the same in every city and every week. A title typed by hand on the
to-do list, of a film Cineville does not show now, is kept by its title until it does."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

STORAGE_KEY = "cineville.seen"
STORAGE_VERSION = 1


def title_key(title: str) -> str:
    return "title:" + " ".join(title.casefold().split())


class SeenFilms:
    """{key: {"title": ..., "at": ISO moment}}; key is the film's id, or title_key() for a title alone."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._films: dict[str, dict[str, str]] = {}
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._films = dict(data.get("films") or {})

    @callback
    def _changed(self) -> None:
        self._store.async_delay_save(lambda: {"films": self._films}, 1)
        for listener in list(self._listeners):
            listener()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def is_seen(self, film_id: str, title: str) -> bool:
        return film_id in self._films or title_key(title) in self._films

    def items(self) -> list[tuple[str, str, datetime | None]]:
        """(key, title, when) of every film seen, the last seen first."""
        out = [(key, v.get("title") or key, dt_util.parse_datetime(v.get("at") or "")) for key, v in self._films.items()]
        far = datetime.min.replace(tzinfo=dt_util.UTC)
        return sorted(out, key=lambda item: item[2] or far, reverse=True)

    @callback
    def add(self, film_id: str | None, title: str) -> str:
        """Mark a film seen, by its id when it has one. A title kept by hand gives way to the id."""
        key = film_id or title_key(title)
        self._films.pop(title_key(title), None)
        self._films[key] = {"title": title, "at": dt_util.utcnow().isoformat()}
        self._changed()
        return key

    @callback
    def remove(self, film_id: str | None, title: str | None = None) -> bool:
        """Unmark a film, by its id, by the key the to-do list shows, or by its title."""
        keys = {k for k in (film_id, title_key(title) if title else None) if k}
        if title:
            keys |= {k for k, v in self._films.items() if title_key(v.get("title") or "") == title_key(title)}
        removed = [self._films.pop(k) for k in keys if k in self._films]
        if removed:
            self._changed()
        return bool(removed)
