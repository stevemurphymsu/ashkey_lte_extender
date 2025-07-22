import requests
import time
from .const import BASE_URL_TEMPLATE, METADATA_PATHS

class AshkeyLTEApi:
    def __init__(self, ip, password):
        self.ip = ip
        self.password = password
        self.token = None
        self.xsrf = None
        self.token_expiry = 0
        self.alarm_defs = {}
        self.reboot_defs = {}

    def base_url(self, path=""):
        return f"{BASE_URL_TEMPLATE.format(ip=self.ip)}/{path}"

    def authenticate(self):
        payload = {
            "expires": "1755791190659^",  # placeholder expiry
            "password": self.password
        }
        response = requests.post(self.base_url("login"), json=payload)
        if response.ok:
            data = response.json()
            self.token = data.get("authtoken")
            self.token_expiry = int(time.time()) + 1800
            self.xsrf = response.cookies.get("X-XSRF-TOKEN")

    def ensure_auth(self):
        if not self.token or time.time() >= self.token_expiry:
            self.authenticate()

    def fetch_data(self, endpoint):
        self.ensure_auth()
        headers = {
            "Authtoken": self.token,
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
        cookies = {"X-XSRF-TOKEN": self.xsrf} if self.xsrf else {}
        url = self.base_url(endpoint)
        response = requests.get(url, headers=headers, cookies=cookies)
        if response.status_code == 401:
            self.authenticate()
            headers["Authtoken"] = self.token
            response = requests.get(url, headers=headers, cookies=cookies)
        return response.json() if response.ok else {}

    def cache_metadata(self):
        self.alarm_defs = self.fetch_data(METADATA_PATHS["alarms"])
        self.reboot_defs = self.fetch_data(METADATA_PATHS["reboots"])
