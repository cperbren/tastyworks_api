import datetime
import logging
from os import environ

import tastyworks.tastyworks_api.tw_api as api

LOGGER = logging.getLogger(__name__)


class TastyAPISession(object):
    def __init__(self):
        self.logged_in = False
        self.logged_in_at = None
        self.session_token = None

    @classmethod
    async def start(cls, username: str = None, password: str = None):
        if not username:
            username = environ.get('TW_USER', "")

        if not password:
            password = environ.get('TW_PASSWORD', "")

        self = TastyAPISession()

        resp = await api.session_start(username, password)

        if api.get_deep_value(resp, ['status', 'code']) == 201:
            self.API_url = 'https://'+api.get_deep_value(resp, ['status', 'host'])
            self.logged_in = True
            self.logged_in_at = datetime.datetime.now()
            self.session_token = api.get_deep_value(resp, ['content', 'data', 'session-token'])
            await self._validate_session()
            return self
        else:
            LOGGER.error(f'Failed to log in. Reason: {api.get_deep_value(resp, ["status", "reason"])}')

    async def is_active(self):
        return await self._validate_session()

    async def _validate_session(self):
        resp = await api.session_validate(self.session_token)

        if api.get_deep_value(resp, ['status', 'code']) == 201:
            return True
        else:
            self.logged_in = False
            self.logged_in_at = None
            self.session_token = None
            LOGGER.error(f'Could not validate the session. Reason: {api.get_deep_value(resp, ["status", "reason"])}')
            return False

    def get_request_headers(self):
        return {
            'Authorization': self.session_token
        }