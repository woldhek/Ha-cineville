"""The films you have seen, as a to-do list: "Cineville seen". Add a title to mark a film seen, delete an item to see it
again in the lists. Every city's list shows the same films."""

from __future__ import annotations

from homeassistant.components.todo import TodoItem, TodoItemStatus, TodoListEntity, TodoListEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CinevilleConfigEntry
from .const import DATA_SEEN, DOMAIN, WEBSITE
from .seen import SeenFilms
from .services import find_film


async def async_setup_entry(hass: HomeAssistant, entry: CinevilleConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SeenList(hass, entry)])


class SeenList(TodoListEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "seen"
    _attr_icon = "mdi:movie-check"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
    )

    def __init__(self, hass: HomeAssistant, entry: CinevilleConfigEntry) -> None:
        self._seen: SeenFilms = hass.data[DATA_SEEN]
        self._attr_unique_id = f"{entry.entry_id}_seen"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Cineville",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=WEBSITE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._seen.async_add_listener(self._refresh))

    @callback
    def _refresh(self) -> None:
        self.async_write_ha_state()

    @property
    def todo_items(self) -> list[TodoItem]:
        return [TodoItem(summary=title, uid=key, status=TodoItemStatus.COMPLETED)
                for key, title, _ in self._seen.items()]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        title = (item.summary or "").strip()
        if not title:
            return
        film, _ = find_film(self.hass, title)
        self._seen.add(film.id if film else None, film.title if film else title)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        # Unticking a film means: not seen after all.
        if item.status == TodoItemStatus.NEEDS_ACTION and item.uid:
            self._seen.remove(item.uid)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            self._seen.remove(uid)
