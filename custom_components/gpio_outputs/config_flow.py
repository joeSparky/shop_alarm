"""Config flow for GPIO Outputs."""

from homeassistant import config_entries

from . import DOMAIN


class GPIOOutputsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GPIO Outputs."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""
        if user_input is not None:
            return self.async_create_entry(
                title="GPIO Outputs",
                data={},
            )

        return self.async_show_form(
            step_id="user",
        )
