"""Switch entities for Alarm Configuration."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
            AlarmConfigurationNotificationSwitch(manager),
            AlarmConfigurationTroubleSwitch(manager),
            AlarmConfigurationChimeOnOpenSwitch(manager),
            AlarmConfigurationChimeOnCloseSwitch(manager),
        ]
    )


class _ManagerSwitch(SwitchEntity):
    _attr_has_entity_name = False

    def __init__(self, manager: AlarmConfigurationManager) -> None:
        self.manager = manager
        self._remove_listener = None

    async def async_added_to_hass(self) -> None:
        self._remove_listener = self.manager.add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener:
            self._remove_listener()


class AlarmConfigurationNotificationSwitch(_ManagerSwitch):
    """Stage the Notification label."""

    _attr_name = "Alarm Configuration Notification"
    _attr_unique_id = "alarm_configuration_notification"
    _attr_icon = "mdi:bell"

    @property
    def is_on(self) -> bool:
        return self.manager.notification

    async def async_turn_on(self, **kwargs) -> None:
        self.manager.set_notification(True)

    async def async_turn_off(self, **kwargs) -> None:
        self.manager.set_notification(False)


class AlarmConfigurationTroubleSwitch(_ManagerSwitch):
    """Stage the Alarm System Trouble label."""

    _attr_name = "Alarm Configuration System Trouble"
    _attr_unique_id = "alarm_configuration_system_trouble"
    _attr_icon = "mdi:alert-circle-check"

    @property
    def is_on(self) -> bool:
        return self.manager.system_trouble

    async def async_turn_on(self, **kwargs) -> None:
        self.manager.set_system_trouble(True)

    async def async_turn_off(self, **kwargs) -> None:
        self.manager.set_system_trouble(False)


class AlarmConfigurationChimeOnOpenSwitch(_ManagerSwitch):
    """Stage the Chime on Open label."""

    _attr_name = "Alarm Configuration Chime on Open"
    _attr_unique_id = "alarm_configuration_chime_on_open"
    _attr_icon = "mdi:bell-ring"

    @property
    def is_on(self) -> bool:
        return self.manager.chime_on_open

    async def async_turn_on(self, **kwargs) -> None:
        self.manager.set_chime_on_open(True)

    async def async_turn_off(self, **kwargs) -> None:
        self.manager.set_chime_on_open(False)


class AlarmConfigurationChimeOnCloseSwitch(_ManagerSwitch):
    """Stage the Chime on Close label."""

    _attr_name = "Alarm Configuration Chime on Close"
    _attr_unique_id = "alarm_configuration_chime_on_close"
    _attr_icon = "mdi:bell-ring"

    @property
    def is_on(self) -> bool:
        return self.manager.chime_on_close

    async def async_turn_on(self, **kwargs) -> None:
        self.manager.set_chime_on_close(True)

    async def async_turn_off(self, **kwargs) -> None:
        self.manager.set_chime_on_close(False)
