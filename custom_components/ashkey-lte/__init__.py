from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN
from .api import AshkeyLTEApi

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ip = entry.data["ip_address"]
    password = entry.data["password"]

    api = AshkeyLTEApi(ip, password)
    api.authenticate()
    api.cache_metadata()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN] = {
        "api": api,
        "auth_token": api.token,
        "xsrf_token": api.xsrf,
        "alarm_defs": api.alarm_defs,
        "reboot_defs": api.reboot_defs,
        "last_alarm": None,
        "last_reboot": None
    }

    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    async def handle_refresh(call):
        api.authenticate()
        hass.data[DOMAIN]["auth_token"] = api.token

    async def handle_reload_metadata(call):
        api.cache_metadata()
        hass.data[DOMAIN]["alarm_defs"] = api.alarm_defs
        hass.data[DOMAIN]["reboot_defs"] = api.reboot_defs

    hass.services.async_register(DOMAIN, "refresh_token", handle_refresh)
    hass.services.async_register(DOMAIN, "reload_metadata", handle_reload_metadata)

    return True
