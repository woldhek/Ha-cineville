"""Cineville: what plays in the Cineville theaters of a city, and what comes soon."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .const import CONF_TRAILER_CAMERA, DATA_SEEN, DOMAIN
from .coordinator import CinevilleCoordinator, setting

PLATFORMS = [Platform.SENSOR, Platform.TODO]
# Experimental, only with the option: a trailer as a camera, and which film it plays.
TRAILER_PLATFORMS = [Platform.CAMERA, Platform.SELECT]
TRAILER_IDS = ("_trailer", "_trailer_film")


def _platforms(entry: ConfigEntry) -> list[Platform]:
    return PLATFORMS + (TRAILER_PLATFORMS if setting(entry, CONF_TRAILER_CAMERA, False) else [])


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
    if not setting(entry, CONF_TRAILER_CAMERA, False):
        # The experiment turned off: its entities leave the registry too, as if it never was.
        registry = er.async_get(hass)
        for suffix in TRAILER_IDS:
            for domain in ("camera", "select"):
                if entity_id := registry.async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}{suffix}"):
                    registry.async_remove(entity_id)
    coordinator.platforms = _platforms(entry)
    await hass.config_entries.async_forward_entry_setups(entry, coordinator.platforms)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CinevilleConfigEntry) -> bool:
    # The platforms it was set up with: the option may have changed since.
    return await hass.config_entries.async_unload_platforms(entry, entry.runtime_data.platforms)


async def _reload(hass: HomeAssistant, entry: CinevilleConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
