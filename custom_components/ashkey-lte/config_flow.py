from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class AshkeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title="ASHKEY LTE",
                data={
                    "ip_address": user_input["ip_address"],
                    "password": user_input["password"]
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("ip_address"): str,
                vol.Required("password"): str
            }),
            errors=errors
        )
