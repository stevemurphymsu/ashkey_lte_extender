from __future__ import annotations

import asyncio
import logging
from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .api import AshkeyLTEApi

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ip = entry.data.get("ip_address")
    password = entry.data.get("password")

    session = async_get_clientsession(hass)
    api = AshkeyLTEApi(ip, password, session)

    try:
        await asyncio.wait_for(api.authenticate(), timeout=10)
        await asyncio.wait_for(api.cache_metadata(), timeout=10)
    except (ClientError, asyncio.TimeoutError, TimeoutError) as net_err:
        _LOGGER.warning("ASHKEY network error during setup: %s", net_err)
        raise ConfigEntryNotReady("ASHKEY device unreachable or network timeout") from net_err
    except (ValueError, KeyError) as parse_err:
        _LOGGER.warning("ASHKEY response parsing error during setup: %s", parse_err)
        raise ConfigEntryNotReady("ASHKEY returned invalid metadata") from parse_err
    except Exception as unknown:
        _LOGGER.exception("Unhandled exception during ASHKEY setup")
        raise ConfigEntryNotReady("Unexpected error during setup") from unknown

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

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    )

    async def handle_refresh(call: ServiceCall) -> None:
        try:
            await asyncio.wait_for(api.authenticate(), timeout=10)
            hass.data[DOMAIN]["auth_token"] = api.token
            _LOGGER.debug("ASHKEY token refreshed successfully")
        except Exception as e:
            _LOGGER.warning("ASHKEY refresh_token service failed: %s", e)

    async def handle_reload_metadata(call: ServiceCall) -> None:
        try:
            await asyncio.wait_for(api.cache_metadata(), timeout=10)
            hass.data[DOMAIN]["alarm_defs"] = api.alarm_defs
            hass.data[DOMAIN]["reboot_defs"] = api.reboot_defs
            _LOGGER.debug("ASHKEY metadata reloaded successfully")
        except Exception as e:
            _LOGGER.warning("ASHKEY reload_metadata service failed: %s", e)

    hass.services.async_register(DOMAIN, "refresh_token", handle_refresh)
    hass.services.async_register(DOMAIN, "reload_metadata", handle_reload_metadata)

    return True
