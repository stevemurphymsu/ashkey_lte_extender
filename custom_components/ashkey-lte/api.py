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
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/"
        }
    
    def base_url(self, path=""):
        if path.startswith("data/"):
            return f"http://{self.ip}/{path}"  # direct root path
        return f"http://{self.ip}/webapi/{path}"

    async def authenticate(self):
        expires_ts = str(int((time.time() + 1800) * 1000)) + "^"
        payload = {
            "expires": expires_ts,
            "password": self.password
        }
        async with self.session.post(self.base_url("login"), json=payload) as response:
            if response.status == 200:
                data = await response.json()
                self.token = data.get("Authtoken")
                self.token_expiry = int(time.time()) + 1800
                self.xsrf = response.cookies.get("X-XSRF-TOKEN")

    async def ensure_auth(self):
        if not self.token or time.time() >= self.token_expiry:
            await self.authenticate()


    async def fetch_data(self, endpoint):
        await self.ensure_auth()
        headers = {
            "Authtoken": self.token,
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
        cookies = {"X-XSRF-TOKEN": self.xsrf} if self.xsrf else {}

        try:
            async with self.session.get(self.base_url(endpoint), headers=headers, cookies=cookies) as response:
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
        self.alarm_defs = await self.fetch_data(self, endpoint="data/alarm.json")
        self.reboot_defs = await self.fetch_data(self, endpoint="data/reboot.json") 
            
    async def get_alarm_log(self) -> dict:
        return await self.fetch_data(self, "alarmLog")
        
    async def get_reboot_log(self) -> dict:
        return await self.fetch_data(self, "rebootLog")

    async def get_about_status(self) -> dict:
        return await self.fetch_data(self, "aboutStatus")