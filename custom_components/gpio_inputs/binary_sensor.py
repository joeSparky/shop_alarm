"""Binary sensors for GPIO Test."""

from datetime import timedelta

import gpiod
from gpiod.line import Bias, Direction, Value

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.event import async_track_time_interval


GPIO_CHIP = "/dev/gpiochip0"

# GPIO numbers to monitor
GPIO_LINES = [17, 19, 22]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up one binary sensor for each configured GPIO line."""
    entities = [GPIOInputBinarySensor(line) for line in GPIO_LINES]
    async_add_entities(entities)


class GPIOInputBinarySensor(BinarySensorEntity):
    """Represent one raw Raspberry Pi GPIO input."""

    def __init__(self, line):
        """Initialize the GPIO input."""
        self._line = line
        self._request = None
        self._remove_listener = None

        self._attr_name = f"GPIO {line}"
        self._attr_unique_id = f"gpio_inputs_{line}"
        self._attr_is_on = False

    async def async_added_to_hass(self):
        """Request the GPIO line and start polling."""
        self._request = gpiod.request_lines(
            GPIO_CHIP,
            consumer=f"home-assistant-gpio-{self._line}",
            config={
                self._line: gpiod.LineSettings(
                    direction=Direction.INPUT,
                    bias=Bias.PULL_UP,
                )
            },
        )

        self._read_gpio()

        self._remove_listener = async_track_time_interval(
            self.hass,
            self._update_gpio,
            timedelta(seconds=1),
        )

    async def _update_gpio(self, now):
        """Read the GPIO periodically."""
        self._read_gpio()
        self.async_write_ha_state()

    def _read_gpio(self):
        """Read the electrical state of this GPIO."""
        value = self._request.get_value(self._line)

        is_high = value == Value.ACTIVE

        # Home Assistant On = electrical HIGH
        # Home Assistant Off = electrical LOW
        self._attr_is_on = is_high

        self._attr_extra_state_attributes = {
            "gpio": self._line,
            "electrical_state": "HIGH" if is_high else "LOW",
        }

    async def async_will_remove_from_hass(self):
        """Release GPIO resources."""
        if self._remove_listener:
            self._remove_listener()

        if self._request:
            self._request.release()