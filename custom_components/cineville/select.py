"""EXPERIMENTAL, with the trailer camera: which film's trailer the camera plays. The action cineville.play_trailer
chooses it too."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CinevilleConfigEntry
from .const import DOMAIN, WEBSITE
from .coordinator import CinevilleCoordinator
from .films import Film


async def async_setup_entry(hass: HomeAssistant, entry: CinevilleConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([TrailerSelect(entry.runtime_data)])


class TrailerSelect(CoordinatorEntity[CinevilleCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "trailer_film"
    _attr_icon = "mdi:movie-play"

    def __init__(self, coordinator: CinevilleCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_trailer_film"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Cineville",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=WEBSITE,
        )

    def _films(self) -> list[Film]:
        data = self.coordinator.data
        out: dict[str, Film] = {}
        for film in ([*data.now, *data.soon] if data else []):
            if film.trailer and film.title not in out:
                out[film.title] = film
        return list(out.values())

    @property
    def options(self) -> list[str]:
        return [f.title for f in self._films()]

    @property
    def current_option(self) -> str | None:
        camera = getattr(self.coordinator, "trailer_camera", None)
        return camera.film.title if camera and camera.film else None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        camera = getattr(self.coordinator, "trailer_camera", None)
        if camera is not None:
            camera.on_change = self._camera_changed

    @callback
    def _camera_changed(self) -> None:
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        camera = getattr(self.coordinator, "trailer_camera", None)
        film = next((f for f in self._films() if f.title == option), None)
        if camera is not None and film is not None:
            camera.set_film(film)
        self.async_write_ha_state()
