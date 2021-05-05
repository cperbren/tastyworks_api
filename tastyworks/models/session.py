import datetime
import logging

import tastyworks.tastyworks_api.tw_api as api

LOGGER = logging.getLogger(__name__)


class TastyAPISession(object):
    def __init__(self):
        self.api_url = None
        self.logged_in = False
        self.logged_in_at = None
        self.session_token = None

    @classmethod
    async def start(cls, username: str = None, password: str = None):
        self = TastyAPISession()

        resp = await api.session_start(username, password)

        if resp.get('status') == 201:
            self.api_url = resp.get('url')
            self.logged_in = True
            self.logged_in_at = datetime.datetime.now()
            self.session_token = resp.get('content').get('data').get('session-token')
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

    # def _get_session_token_v2(self):
    #     self.logged_in = False
    #     if self.logged_in and self.session_token:
    #         if (datetime.datetime.now() - self.logged_in_at).total_seconds() < 60:
    #             return self.session_token
    #
    #     loop = asyncio.new_event_loop()
    #     resp = loop.run_until_complete(api.session_start(self.username, self.password))
    #
    #     if resp.get('status') == 201:
    #         self.logged_in = True
    #         self.logged_in_at = datetime.datetime.now()
    #         self.session_token = resp.get('content').get('data').get('session-token')
    #         self._validate_session_v2()
    #         return self.session_token
    #     else:
    #         self.logged_in = False
    #         self.logged_in_at = None
    #         self.session_token = None
    #         LOGGER.error(f'Failed to log in. Reason: {resp.get("reason")}')
    #
    # def _validate_session_v2(self):
    #     loop = asyncio.new_event_loop()
    #     resp = loop.run_until_complete(api.session_validate(self.session_token))
    #
    #     if resp.get('status') == 201:
    #         return True
    #     else:
    #         self.logged_in = False
    #         self.logged_in_at = None
    #         self.session_token = None
    #         LOGGER.error(f'Could not validate the session. Reason: {resp.get("reason")}')
    #         return False
    #
