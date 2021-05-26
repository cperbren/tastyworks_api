import logging
import asyncio
from os import environ
from datetime import datetime
from dataclasses import dataclass

import tastyworks.tastyworks_api.tw_api as api

LOGGER = logging.getLogger(__name__)


@dataclass
class TastyAPISession(object):
    session_token: str = None
    logged_in: bool = False
    logged_in_at: datetime = None
    validated: bool = None
    validated_at: datetime = None

    @classmethod
    async def start(cls, username: str = None, password: str = None):
        max_retries = 3  # Note there seems to be some limitation on failed validation per IP
        tries = 1

        if not username:
            username = environ.get('TW_USER', "")
        if not password:
            password = environ.get('TW_PASSWORD', "")

        session = cls()

        while not session.validated or tries == max_retries:
            tries += 1

            response = await api.session_start(username, password)

            if api.get_deep_value(response, ['status', 'code']) != 201:
                LOGGER.error(f'Failed to log in: {api.get_deep_value(response, ["status", "reason"])}. Retrying.')
                continue

            session.logged_in = True
            session.logged_in_at = datetime.now()
            session.session_token = api.get_deep_value(response, ['content', 'data', 'session-token'])

            await session._validate_session()

            if not session.validated:
                # Sleeping a bit to avoid issues with API IP rates
                LOGGER.warning('Could not start the session. Trying again in 5 seconds.')
                await asyncio.sleep(5)

        if not session.validated:
            LOGGER.error('Could not start the session. Giving up.')
            raise
        else:
            return session

    async def is_active(self):
        return await self._validate_session()

    async def _validate_session(self):
        resp = await api.session_validate(self.session_token)

        if api.get_deep_value(resp, ['status', 'code']) == 201:
            self.validated = True
            self.validated_at = datetime.now()
            LOGGER.info(f'Session validated.')
            return True
        else:
            self.logged_in = False
            self.logged_in_at = None
            self.session_token = None
            self.validated = False
            self.validated_at = None
            LOGGER.error(f'Could not validate the session. Reason: {api.get_deep_value(resp, ["status", "reason"])}')
            return False
