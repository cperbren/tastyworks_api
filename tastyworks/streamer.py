import datetime
import logging

import aiocometd
from aiocometd import ConnectionType

from tastyworks import dxfeed
from tastyworks.dxfeed import mapper as dxfeed_mapper
from tastyworks.models.session import TastyAPISession

import tastyworks.tastyworks_api.tw_api as api

LOGGER = logging.getLogger(__name__)


class DataStreamer(object):
    def __init__(self):
        self.data = None
        self.token = None
        self.websocket_url = None
        self.tasty_session = None
        self.cometd_client = None
        self.data_created = None
        self.subs = {}

    async def close(self):
        await self.cometd_client.close()

    @classmethod
    async def start(cls, session: TastyAPISession):
        self = DataStreamer()
        self.tasty_session = session
        if not await session.is_active():
            await session.start()
        await self._setup_connection()
        return self

    async def _cometd_close(self):
        await self.cometd_client.close()

    async def add_data_sub(self, values):
        LOGGER.debug(f'Adding subscription: {values}')
        await self._send_msg(dxfeed.SUBSCRIPTION_CHANNEL, {'add': values})

    async def remove_data_sub(self, values):
        # NOTE: Experimental, unconfirmed. Needs testing
        LOGGER.info(f'Removing subscription: {values}')
        await self._send_msg(dxfeed.SUBSCRIPTION_CHANNEL, {'remove': values})

    async def _consumer(self, message):
        return dxfeed_mapper.map_message(message)

    async def _send_msg(self, channel, message):
        if not self.logged_in:
            raise Exception('Connection not made or logged in')
        LOGGER.debug('[dxFeed] sending: %s on channel: %s', message, channel)
        await self.cometd_client.publish(channel, message)

    async def reset_data_subs(self):
        LOGGER.debug('Resetting data subscriptions')
        await self._send_msg(dxfeed.SUBSCRIPTION_CHANNEL, {'reset': True})

    async def _get_streamer_data(self):
        if hasattr(self, 'streamer_data_created') \
                and (datetime.datetime.now() - self.data_created).total_seconds() < 60:
            return self.data

        resp = await api.get_streamer_info(self.tasty_session.session_token)

        if api.get_deep_value(resp, ['status', 'code']) != 200:
            self.error = api.get_deep_value(resp, ['status', 'reason'])
            LOGGER.error(f'Could not get quote streamer data, error message: {self.error}')
        else:
            self.data = resp.get('content').get('data')
            self.websocket_url = self._get_streamer_websocket_url()
            self.token = self.data.get('token')
            self.data_created = datetime.datetime.now()
        return resp

    def _get_streamer_websocket_url(self):
        return f'{self.data.get("websocket-url")}/cometd'

    async def _setup_connection(self):
        aiocometd.client.DEFAULT_CONNECTION_TYPE = ConnectionType.WEBSOCKET

        await self._get_streamer_data()

        LOGGER.info('Connecting to url: %s', self.websocket_url)

        auth_extension = AuthExtension(self.data.get('token'))
        cometd_client = aiocometd.Client(
            self.websocket_url,
            auth=auth_extension,
        )
        await cometd_client.open()
        await cometd_client.subscribe(dxfeed.DATA_CHANNEL)

        self.cometd_client = cometd_client
        self.logged_in = True
        LOGGER.info('Connected and logged in to dxFeed data stream')

        await self.reset_data_subs()

        return True

    async def listen(self):
        async for msg in self.cometd_client:
            LOGGER.debug('[dxFeed] received: %s', msg)
            if msg['channel'] != dxfeed.DATA_CHANNEL:
                continue
            yield await self._consumer(msg['data'])


class AuthExtension(aiocometd.AuthExtension):
    def __init__(self, streamer_token: str):
        self.streamer_token = streamer_token

    def _get_login_msg(self):
        return {'ext': {'com.devexperts.auth.AuthToken': f'{self.streamer_token}'}}

    def _get_advice_msg(self):
        return {
            'timeout': 60 * 1000,
            'interval': 0
        }

    async def incoming(self, payload, headers=None):
        pass

    async def outgoing(self, payload, headers=None):
        for entry in payload:
            if 'clientId' not in entry:
                entry.update(self._get_login_msg())

    async def authenticate(self):
        pass
