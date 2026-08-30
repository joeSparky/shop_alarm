"""Select entities for Alarm Configuration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, SECURITY_OPTIONS
from .manager import AlarmConfigurationManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager: AlarmConfigurationManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AlarmConfigurationEntitySelect(manager),
            AlarmConfigurationSecurityRoleSelect(manager),
        ]
    )


class _ManagerSelect(SelectEntity):
    _attr_has_entity_name = False

    def __init__(self, manager: AlarmConfigurationManager) -> None:
        self.manager = manager
        self._remove_listener = None

    async def async_added_to_hass(self) -> None:
        self._remove_listener = self.manager.add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener:
            self._remove_listener()


class AlarmConfigurationEntitySelect(_ManagerSelect):
    """Choose the entity whose alarm roles are being edited."""

    _attr_name = "Alarm Configuration Entity"
    _attr_unique_id = "alarm_configuration_entity"
    _attr_icon = "mdi:devices"

    @property
    def options(self) -> list[str]:
        return self.manager.entity_options

    @property
    def current_option(self) -> str | None:
        return self.manager.selected_entity_option

    async def async_select_option(self, option: str) -> None:
        self.manager.select_entity_option(option)


class AlarmConfigurationSecurityRoleSelect(_ManagerSelect):
    """Choose the mutually-exclusive security role."""

    _attr_name = "Alarm Configuration Security Role"
    _attr_unique_id = "alarm_configuration_security_role"
    _attr_icon = "mdi:shield"

    @property
    def options(self) -> list[str]:
        return list(SECURITY_OPTIONS)

    @property
    def current_option(self) -> str:
        return self.manager.security_role

    async def async_select_option(self, option: str) -> None:
        self.manager.set_security_role(option)
