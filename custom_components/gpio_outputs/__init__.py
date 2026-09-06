"""GPIO Outputs integration for Home Assistant."""

from homeassistant.const import Platform

DOMAIN = "gpio_outputs"

PLATFORMS = [Platform.SWITCH]


async def async_setup(hass, config):
    """Set up GPIO Outputs from YAML."""
    return True


async def async_setup_entry(hass, entry):
    """Set up GPIO Outputs from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    """Unload a GPIO Outputs config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
