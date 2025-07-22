import time
from aiohttp import ClientSession
from .const import BASE_URL_TEMPLATE, METADATA_PATHS

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
                self.token = data.get("authtoken")
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

        async with self.session.get(self.base_url(endpoint), headers=headers, cookies=cookies) as response:
            if response.status == 401:
                await self.authenticate()
                headers["Authtoken"] = self.token
                async with self.session.get(self.base_url(endpoint), headers=headers, cookies=cookies) as retry_response:
                    return await retry_response.json() if retry_response.status == 200 else {}
            return await response.json() if response.status == 200 else {}

    async def cache_metadata(self):
        self.alarm_defs = await self.fetch_data(METADATA_PATHS["alarms"])
        self.reboot_defs = await self.fetch_data(METADATA_PATHS["reboots"])
