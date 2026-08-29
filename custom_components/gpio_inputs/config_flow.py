"""Config flow for GPIO Test."""

from homeassistant import config_entries

from . import DOMAIN


class GPIOTestConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GPIO Test."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""
        if user_input is not None:
            return self.async_create_entry(
                title="GPIO Test",
                data={},
            )

        return self.async_show_form(
            step_id="user",
        )