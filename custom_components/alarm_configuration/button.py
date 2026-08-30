"""Button entities for Alarm Configuration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .manager import AlarmConfigurationManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager: AlarmConfigurationManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AlarmConfigurationApplyButton(manager),
            AlarmConfigurationRefreshButton(manager),
        ]
    )


class _ManagerButton(ButtonEntity):
    _attr_has_entity_name = False

    def __init__(self, manager: AlarmConfigurationManager) -> None:
        self.manager = manager


class AlarmConfigurationApplyButton(_ManagerButton):
    """Apply staged roles to the selected entity."""

    _attr_name = "Alarm Configuration Apply"
    _attr_unique_id = "alarm_configuration_apply"
    _attr_icon = "mdi:content-save-check"

    async def async_press(self) -> None:
        self.manager.apply()


class AlarmConfigurationRefreshButton(_ManagerButton):
    """Refresh the list of candidate entities."""

    _attr_name = "Alarm Configuration Refresh Entities"
    _attr_unique_id = "alarm_configuration_refresh_entities"
    _attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        self.manager.refresh_candidates()
