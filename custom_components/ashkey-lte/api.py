import time
from aiohttp import ClientSession
from .const import BASE_URL_TEMPLATE, METADATA_PATHS
import json
import logging

_LOGGER = logging.getLogger(__name__)

class AshkeyLTEApi:
    def __init__(self, ip, password, session: ClientSession):
        self.ip = ip
        self.password = password
        self.session = session
        self.token = None
        self.xsrf = None
        self.token_expiry = 0
        self.alarm_defs = {}
        self.reboot_defs = {}

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "Authtoken": self.token or "",
            "X-Requested-With": "XMLHttpRequest"
        }

    @property
    def cookies(self):
        return {
            "X-XSRF-TOKEN": self.xsrf,
            "Authtoken": self.token
        }
    
    def base_url(self, path=""):
        if path.startswith("data/"):
            return f"https://{self.ip}/{path}"  # direct root path
        return f"https://{self.ip}/webapi/{path}"

    async def authenticate(self):
        expires_ts = str(int((time.time() + 1800) * 1000))
        try:
            async with self.session.post(f"https://{self.ip}/webapi/login?password={self.password}&expires={expires_ts}", headers=self.headers, ssl=False) as response:            
                data = await response.json()
                self.token = data.get("Authtoken")
                self.token_expiry = data.get("expires")
                self.xsrf = response.cookies.get("X-XSRF-TOKEN")
                self.alarm_log = await self.get_alarm_log()
                self.reboot_log = await self.get_reboot_log()
        except Exception as e:
            _LOGGER.error("ASHKEY: Exception during authentication %s", e)
            return {}
        
    async def fetch_data(self, endpoint):
        try:
            async with self.session.get(self.base_url(endpoint), headers=self.headers, cookies=self.cookies, ssl=False) as response:
                if response.status == 200:
                    text = await response.text()
                    return json.loads(text)
                else:
                    _LOGGER.warning("ASHKEY: Bad response %s for endpoint %s", response.status, endpoint)
                    return {}
        except Exception as e:
            _LOGGER.error("ASHKEY: Exception while fetching %s: %s", endpoint, e)
            return {}

    async def cache_metadata(self):
        self.alarm_defs = await self.fetch_data("data/alarm.json")
        self.reboot_defs = await self.fetch_data("data/reboot.json") 
            
    async def get_alarm_log(self) -> dict:
        return await self.fetch_data("alarmLog")
        
    async def get_reboot_log(self) -> dict:
        return await self.fetch_data("rebootLog")

    async def get_about_status(self) -> dict:
        return await self.fetch_data("aboutStatus")