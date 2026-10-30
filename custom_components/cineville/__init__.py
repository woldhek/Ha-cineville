"""Cineville: what plays in the Cineville theaters of a city, and what comes soon."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DATA_SEEN, DOMAIN
from .coordinator import CinevilleCoordinator

PLATFORMS = [Platform.SENSOR, Platform.TODO]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type CinevilleConfigEntry = ConfigEntry[CinevilleCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Once for every city: the list of films seen, and the actions."""
    from . import services
    from .seen import SeenFilms

    seen = SeenFilms(hass)
    await seen.async_load()
    hass.data[DATA_SEEN] = seen
    services.async_register(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CinevilleConfigEntry) -> bool:
    coordinator = CinevilleCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CinevilleConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _reload(hass: HomeAssistant, entry: CinevilleConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
