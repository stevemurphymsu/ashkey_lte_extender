from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator
)
from homeassistant.helpers.event import async_call_later
from datetime import timedelta
import logging
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN]["api"]

    async def async_update_data():
        sim = api.fetch_data("simStatus")
        advanced = api.fetch_data("advanced")
        devices = api.fetch_data("devices")
        gps = api.fetch_data("gps")
        perf = api.fetch_data("performance")
        about = api.fetch_data("aboutStatus")
        alarm_data = api.fetch_data("alarmLog")
        reboot_data = api.fetch_data("rebootLog")

        latest_alarm = alarm_data.get("alarmHistoryList", [{}])[-1]
        latest_reboot = reboot_data.get("rebootHistoryList", [{}])[-1]

        alarm_defs = hass.data[DOMAIN]["alarm_defs"]
        reboot_defs = hass.data[DOMAIN]["reboot_defs"]
        alarm_detail = alarm_defs.get(latest_alarm.get("alarmId"), {})
        reboot_reason = reboot_defs.get(str(latest_reboot.get("rebootReason")), {}).get("rebootReason", "Unknown")

        # Fire events if changed
        if latest_alarm != hass.data[DOMAIN]["last_alarm"]:
            hass.bus.async_fire("ashkey_alarm_event", {**latest_alarm, **alarm_detail})
            hass.data[DOMAIN]["last_alarm"] = latest_alarm

        if latest_reboot != hass.data[DOMAIN]["last_reboot"]:
            hass.bus.async_fire("ashkey_reboot_event", {**latest_reboot, "reason": reboot_reason})
            hass.data[DOMAIN]["last_reboot"] = latest_reboot

        current_bw = perf.get("CurrentBandWidth", [])[-1] if perf.get("CurrentBandWidth") else {}
        hourly_bw = perf.get("HourlyBandWidth", [])[-1] if perf.get("HourlyBandWidth") else {}
        gps_qualities = gps.get("HourlySatelliteQualities", [])[-1] if gps.get("HourlySatelliteQualities") else {}

        return {
            "gps_status": sim.get("gpsStatus"),
            "macAddress": sim.get("macAddress"),
            "serial": sim.get("serial"),
            "bhIpv4Addr": sim.get("bhIpv4Addr"),
            "lati": sim.get("lati"),
            "longi": sim.get("longi"),
            "FourGsignal": sim.get("FourGsignal"),
            "uptime": sim.get("uptime"),
            "operationMode": sim.get("operationMode"),
            "txPower": advanced.get("txPower"),
            "earfcn": advanced.get("earfcn"),
            "pci": advanced.get("pci"),
            "activeUECountTot": devices.get("activeUECountTot"),
            "peakCapacityUsedLastHourTot": devices.get("peakCapacityUsedLastHourTot"),
            "gps_satellite_count": len(gps.get("GpsList", [])),
            "gps_satellite_avg_quality": gps_qualities.get("Avg"),
            "gps_satellite_max_quality": gps_qualities.get("Max"),
            "gps_satellite_min_quality": gps_qualities.get("Min"),
            "current_uplink": current_bw.get("Uplink"),
            "current_downlink": current_bw.get("Downlink"),
            "hourly_uplink": hourly_bw.get("Uplink"),
            "hourly_downlink": hourly_bw.get("Downlink"),
            "last_alarm_name": latest_alarm.get("alarmName"),
            "last_alarm_time": latest_alarm.get("alarmTime"),
            "last_alarm_severity": alarm_detail.get("troubleshooting"),
            "last_reboot_reason": reboot_reason,
            "last_reboot_time": latest_reboot.get("rebootTime"),
            "lcd_page_event": about.get("lcdDisplay", {}).get("pageEvent"),
            "lcd_datetime": about.get("lcdDisplay", {}).get("datetime"),
        }

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="ashkey_lte",
        update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    entities = []
    for key, label in coordinator.data.items():
        entities.append(AshkeyLTESensor(coordinator, key, label))
    async_add_entities(entities)

class AshkeyLTESensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"ashkey_lte_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)
