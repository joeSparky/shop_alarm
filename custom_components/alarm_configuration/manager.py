"""Shared state and label-registry operations for Alarm Configuration."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr

from .const import (
    DOMAIN,
    LABEL_DELAYED,
    LABEL_IMMEDIATE,
    LABEL_NOTIFICATION,
    LABEL_TROUBLE,
    MANAGED_LABEL_NAMES,
    SECURITY_DELAYED,
    SECURITY_IMMEDIATE,
    SECURITY_NONE,
)


class AlarmConfigurationManager:
    """Hold staged configuration and apply it to Home Assistant labels."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.selected_entity_id: str | None = None
        self.security_role = SECURITY_NONE
        self.notification = False
        self.system_trouble = False
        self.status = "Select an entity"
        self._listeners: list[Callable[[], None]] = []
        self._option_to_entity: dict[str, str] = {}
        self._entity_to_option: dict[str, str] = {}

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an entity-state refresh callback."""
        self._listeners.append(listener)

        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    def ensure_labels(self) -> None:
        """Create the four managed labels if they do not already exist."""
        registry = lr.async_get(self.hass)
        for name in MANAGED_LABEL_NAMES:
            if registry.async_get_label_by_name(name) is None:
                registry.async_create(name)

    def _label_id(self, name: str) -> str:
        registry = lr.async_get(self.hass)
        label = registry.async_get_label_by_name(name)
        if label is None:
            label = registry.async_create(name)
        return label.label_id

    def refresh_candidates(self) -> list[str]:
        """Build a useful display-name list for configurable alarm devices."""
        registry = er.async_get(self.hass)
        candidates: list[tuple[str, str]] = []

        managed_label_ids = {
            self._label_id(name) for name in MANAGED_LABEL_NAMES
        }

        # Binary-sensor classes that commonly make sense for alarm/security
        # inputs.  This intentionally removes infrastructure/status sensors
        # such as connectivity, battery, running, and update entities.
        alarm_binary_device_classes = {
            "carbon_monoxide",
            "door",
            "gas",
            "garage_door",
            "lock",
            "moisture",
            "motion",
            "occupancy",
            "opening",
            "presence",
            "problem",
            "safety",
            "smoke",
            "tamper",
            "vibration",
            "window",
        }

        for entry in registry.entities.values():
            entity_id = entry.entity_id
            domain = entity_id.split(".", 1)[0]

            if entry.platform == DOMAIN:
                continue

            labels = set(entry.labels)
            already_managed = bool(labels & managed_label_ids)

            # Never hide an entity that is already participating in the alarm,
            # even if its domain/device class is unusual.
            if not already_managed:
                if domain == "binary_sensor":
                    # Package/template status entities are not physical alarm
                    # devices and should not appear in Device Configuration.
                    if entry.platform == "template":
                        continue

                    state = self.hass.states.get(entity_id)
                    device_class = None
                    if state is not None:
                        device_class = state.attributes.get("device_class")

                    # GPIO contact inputs may intentionally have no device class.
                    if (
                        device_class not in alarm_binary_device_classes
                        and not (
                            device_class is None
                            and entry.platform == "gpio_inputs"
                        )
                    ):
                        continue

                elif domain == "switch":
                    # Keep switches available because relay outputs such as a
                    # siren relay can participate in System Trouble monitoring.
                    pass
                else:
                    continue

            state = self.hass.states.get(entity_id)
            if state is not None:
                friendly = state.name
            elif entry.name:
                friendly = entry.name
            elif entry.original_name:
                friendly = entry.original_name
            else:
                friendly = entity_id

            candidates.append((friendly, entity_id))

        candidates.sort(key=lambda item: (item[0].casefold(), item[1]))

        # Friendly names are allowed to repeat, so always include the entity ID.
        self._option_to_entity = {
            f"{friendly} — {entity_id}": entity_id
            for friendly, entity_id in candidates
        }
        self._entity_to_option = {
            entity_id: option for option, entity_id in self._option_to_entity.items()
        }

        if self.selected_entity_id not in self._entity_to_option:
            self.selected_entity_id = candidates[0][1] if candidates else None
            if self.selected_entity_id:
                self.load_selected()
            else:
                self.status = "No configurable alarm devices found"

        self._notify()
        return list(self._option_to_entity)

    @property
    def entity_options(self) -> list[str]:
        if not self._option_to_entity:
            self.refresh_candidates()
        return list(self._option_to_entity)

    @property
    def selected_entity_option(self) -> str | None:
        if self.selected_entity_id is None:
            return None
        return self._entity_to_option.get(self.selected_entity_id)

    def select_entity_option(self, option: str) -> None:
        entity_id = self._option_to_entity.get(option)
        if entity_id is None:
            raise ValueError(f"Unknown entity selection: {option}")
        self.selected_entity_id = entity_id
        self.load_selected()

    def load_selected(self) -> None:
        """Load managed labels for the selected entity into staged controls."""
        if self.selected_entity_id is None:
            return

        registry = er.async_get(self.hass)
        entry = registry.async_get(self.selected_entity_id)
        if entry is None:
            self.status = f"Entity not found: {self.selected_entity_id}"
            self._notify()
            return

        labels = set(entry.labels)
        delayed_id = self._label_id(LABEL_DELAYED)
        immediate_id = self._label_id(LABEL_IMMEDIATE)
        notification_id = self._label_id(LABEL_NOTIFICATION)
        trouble_id = self._label_id(LABEL_TROUBLE)

        if immediate_id in labels:
            self.security_role = SECURITY_IMMEDIATE
        elif delayed_id in labels:
            self.security_role = SECURITY_DELAYED
        else:
            self.security_role = SECURITY_NONE

        self.notification = notification_id in labels
        self.system_trouble = trouble_id in labels
        self.status = f"Loaded {self.selected_entity_id}"
        self._notify()

    def set_security_role(self, role: str) -> None:
        if role not in (SECURITY_NONE, SECURITY_DELAYED, SECURITY_IMMEDIATE):
            raise ValueError(f"Unsupported security role: {role}")
        self.security_role = role
        self._notify()

    def set_notification(self, enabled: bool) -> None:
        self.notification = enabled
        self._notify()

    def set_system_trouble(self, enabled: bool) -> None:
        self.system_trouble = enabled
        self._notify()

    def apply(self) -> None:
        """Apply the staged roles while preserving unrelated labels."""
        if self.selected_entity_id is None:
            self.status = "No entity selected"
            self._notify()
            return

        registry = er.async_get(self.hass)
        entry = registry.async_get(self.selected_entity_id)
        if entry is None:
            self.status = f"Entity not found: {self.selected_entity_id}"
            self._notify()
            return

        delayed_id = self._label_id(LABEL_DELAYED)
        immediate_id = self._label_id(LABEL_IMMEDIATE)
        notification_id = self._label_id(LABEL_NOTIFICATION)
        trouble_id = self._label_id(LABEL_TROUBLE)

        labels = set(entry.labels)

        # Delayed and Immediate are deliberately mutually exclusive.
        labels.discard(delayed_id)
        labels.discard(immediate_id)
        if self.security_role == SECURITY_DELAYED:
            labels.add(delayed_id)
        elif self.security_role == SECURITY_IMMEDIATE:
            labels.add(immediate_id)

        if self.notification:
            labels.add(notification_id)
        else:
            labels.discard(notification_id)

        if self.system_trouble:
            labels.add(trouble_id)
        else:
            labels.discard(trouble_id)

        registry.async_update_entity(self.selected_entity_id, labels=labels)
        self.status = f"Applied roles to {self.selected_entity_id}"
        self.load_selected()
