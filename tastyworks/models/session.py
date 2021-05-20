import datetime
import logging

import tastyworks.tastyworks_api.tw_api as api

LOGGER = logging.getLogger(__name__)


class TastyAPISession(object):
    def __init__(self, username: str = None, password: str = None, API_url = None):
        # self.API_url = API_url if API_url else 'https://api.tastyworks.com'
        # self.username = username
        # self.password = password
        self.logged_in = False
        self.logged_in_at = None
        self.session_token = None

    @classmethod
    async def start(cls, username: str = None, password: str = None):
        self = TastyAPISession()

        resp = await api.session_start(username, password)

        if resp.get('status') == 201:
            self.API_url = 'https://'+resp.get('host')
            self.logged_in = True
            self.logged_in_at = datetime.datetime.now()
            self.session_token = api.get_deep_value(resp, ['content', 'data', 'session-token'])
            await self._validate_session()
            return self
        else:
            LOGGER.error(f'Failed to log in. Reason: {resp.get("reason")}')

    async def is_active(self):
        return await self._validate_session()

    async def _validate_session(self):
        resp = await api.session_validate(self.session_token)

        if resp.get('status') == 201:
            return True
        else:
            self.logged_in = False
            self.logged_in_at = None
            self.session_token = None
            LOGGER.error(f'Could not validate the session. Reason: {resp.get("reason")}')
            return False

    def get_request_headers(self):
        return {
            'Authorization': self.session_token
        }