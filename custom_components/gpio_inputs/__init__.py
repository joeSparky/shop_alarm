"""GPIO Test integration for Home Assistant."""

from homeassistant.const import Platform

DOMAIN = "gpio_inputs"

PLATFORMS = [Platform.BINARY_SENSOR]


async def async_setup(hass, config):
    """Set up GPIO Test from YAML."""
    return True


async def async_setup_entry(hass, entry):
    """Set up GPIO Test from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    """Unload a GPIO Test config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)