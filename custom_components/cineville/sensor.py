"""Two sensors per city: the films that play (state: how many), and the films that come soon."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import CinevilleConfigEntry
from .const import ATTRIBUTION, CONF_HIDE_SEEN, DATA_SEEN, DEFAULT_HIDE_SEEN, DETAILED_FILMS, DOMAIN, WEBSITE
from .coordinator import CinevilleCoordinator, setting
from .films import Film, compact

# Lists change with every update and are long: keep them out of the recorder's history.
_LISTS = frozenset({"films", "titles", "highlights", "directors", "shows", "shows_today", "next_start", "next_venue",
                    "premieres", "venues", "ids", "hidden_seen"})


async def async_setup_entry(hass: HomeAssistant, entry: CinevilleConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([CinevilleSensor(coordinator, "now"), CinevilleSensor(coordinator, "soon")])


class CinevilleSensor(CoordinatorEntity[CinevilleCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_native_unit_of_measurement = "films"
    _unrecorded_attributes = _LISTS

    def __init__(self, coordinator: CinevilleCoordinator, kind: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._kind = kind
        self._attr_unique_id = f"{entry.entry_id}_{kind}"
        self._attr_translation_key = "now_showing" if kind == "now" else "coming_soon"
        self._attr_icon = "mdi:movie-open-star" if kind == "now" else "mdi:movie-open-plus"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Cineville",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=WEBSITE,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # A film marked seen leaves the lists at once, without asking Cineville again.
        self.async_on_remove(self.hass.data[DATA_SEEN].async_add_listener(self._seen_changed))

    @callback
    def _seen_changed(self) -> None:
        self.async_write_ha_state()

    def _all(self) -> list[Film]:
        data = self.coordinator.data
        return (data.now if self._kind == "now" else data.soon) if data else []

    def _films(self) -> list[Film]:
        """The films of the list, without those seen when the option hides them."""
        films = self._all()
        if not setting(self.coordinator.config_entry, CONF_HIDE_SEEN, DEFAULT_HIDE_SEEN):
            return films
        seen = self.hass.data[DATA_SEEN]
        return [f for f in films if not seen.is_seen(f.id, f.title)]

    @property
    def native_value(self) -> int:
        return len(self._films())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data:
            return {}
        zone = dt_util.get_default_time_zone()
        films = self._films()
        attributes = compact(films, self._kind, zone)
        attributes["city"] = data.city
        attributes["venues"] = data.venues
        seen = self.hass.data[DATA_SEEN]
        attributes["films"] = [{**f.detail(zone), "seen": seen.is_seen(f.id, f.title)} for f in films[:DETAILED_FILMS]]
        attributes["hidden_seen"] = len(self._all()) - len(films)
        return attributes
