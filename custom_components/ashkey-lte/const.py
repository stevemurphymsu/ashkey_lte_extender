DOMAIN = "ashkey-lte"
BASE_URL_TEMPLATE = "https://{ip}/webapi"
METADATA_PATHS = {
    "alarms": "data/alarm.json",
    "reboots": "data/reboot.json"
}
DEFAULT_SCAN_INTERVAL = 30  # seconds
EVENT_ALARM = "ashkey_alarm_event"
EVENT_REBOOT = "ashkey_reboot_event"
