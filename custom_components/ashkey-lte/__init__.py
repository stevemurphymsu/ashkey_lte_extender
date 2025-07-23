from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from aiohttp import ClientError
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .api import AshkeyLTEApi

_LOGGER = logging.getLogger(__name__)

class AshkeyDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the ASHKEY LTE device."""
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, api: AshkeyLTEApi) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name="ASHKEY LTE Data Coordinator",
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=30)
        )
        self.api = api

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        try:
            await self.api.authenticate()
        except Exception as err:
            raise ConfigEntryAuthFailed from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:           
            # Fetch updated data
            alarm_log = await self.api.get_alarm_log()
            reboot_log = await self.api.get_reboot_log()
            about_status = await self.api.get_about_status()
            
            return {
                "alarm_log": alarm_log,
                "reboot_log": reboot_log,
                "about_status": about_status,
                "auth_token": self.api.token,
                "xsrf_token": self.api.xsrf,
                "alarm_defs": self.api.alarm_defs,
                "reboot_defs": self.api.reboot_defs
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        
class MyEntity(CoordinatorEntity):
    def __init__(self, coordinator, idx):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        #self._attr_is_on = self.coordinator.data[self.idx]["state"]
        self.async_write_ha_state()
    

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> bool:
    """Set up ASHKEY LTE from a config entry."""
    ip = entry.data.get("ip_address")
    password = entry.data.get("password")
    
    session = async_get_clientsession(hass)
    api = AshkeyLTEApi(ip, password, session)
    coordinator = AshkeyDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        MyEntity(coordinator, idx) for idx, ent in enumerate(coordinator.data)
    )

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
