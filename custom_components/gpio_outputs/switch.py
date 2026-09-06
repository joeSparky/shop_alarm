"""Switch entities for GPIO Outputs."""

import gpiod
from gpiod.line import Direction, Value

from homeassistant.components.switch import SwitchEntity


GPIO_CHIP = "/dev/gpiochip0"

# Raw GPIO outputs exposed to Home Assistant. Uses BCM GPIO numbering.
GPIO_LINES = [18, 23]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up one switch for each configured GPIO output line."""
    entities = [GPIOOutputSwitch(line) for line in GPIO_LINES]
    async_add_entities(entities)


class GPIOOutputSwitch(SwitchEntity):
    """Represent one raw Raspberry Pi GPIO output."""

    def __init__(self, line):
        """Initialize the GPIO output."""
        self._line = line
        self._request = None

        self._attr_name = f"GPIO {line}"
        self._attr_unique_id = f"gpio_outputs_{line}"
        self._attr_is_on = False

    async def async_added_to_hass(self):
        """Request the GPIO line and initialize it LOW/OFF."""
        self._request = gpiod.request_lines(
            GPIO_CHIP,
            consumer=f"home-assistant-gpio-output-{self._line}",
            config={
                self._line: gpiod.LineSettings(
                    direction=Direction.OUTPUT,
                    output_value=Value.INACTIVE,
                )
            },
        )

        self._attr_is_on = False
        self._update_attributes()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Drive the GPIO output HIGH."""
        if self._request is None:
            return

        self._request.set_value(self._line, Value.ACTIVE)
        self._attr_is_on = True
        self._update_attributes()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Drive the GPIO output LOW."""
        if self._request is None:
            return

        self._request.set_value(self._line, Value.INACTIVE)
        self._attr_is_on = False
        self._update_attributes()
        self.async_write_ha_state()

    def _update_attributes(self):
        """Expose useful diagnostic information."""
        self._attr_extra_state_attributes = {
            "gpio": self._line,
            "electrical_state": "HIGH" if self._attr_is_on else "LOW",
        }

    async def async_will_remove_from_hass(self):
        """Return the GPIO LOW before releasing it."""
        if self._request:
            self._request.set_value(self._line, Value.INACTIVE)
            self._request.release()
            self._request = None
