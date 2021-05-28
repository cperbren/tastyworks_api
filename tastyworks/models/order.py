import logging
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List
from dataclasses import dataclass, field

import tastyworks.tastyworks_api.tw_api as api
from tastyworks.tastyworks_api.session import TastyAPISession
from tastyworks.tastyworks_api.messages import OrderError, OrderWarning

LOGGER = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = 'Market'
    LIMIT = 'Limit'
    STOP_MARKET = 'Stop'
    STOP_LIMIT = 'Stop Limit'
    NOTIONAL = 'Notional Market'  # Used for cryptos


class OrderPriceEffect(Enum):
    CREDIT = 'Credit'
    DEBIT = 'Debit'


class OrderPriceEffectSign(Enum):
    Credit = 1
    Debit = -1


class OrderStatus(Enum):
    ROUTED = 'Routed'
    RECEIVED = 'Received'
    CANCELLED = 'Cancelled'
    CANCEL_REQ = 'Cancel Requested'
    FILLED = 'Filled'
    EXPIRED = 'Expired'
    LIVE = 'Live'
    REJECTED = 'Rejected'
    CONTINGENT = 'Contingent'

    def is_active(self):
        return self in (OrderStatus.LIVE, OrderStatus.RECEIVED)


class TimeInForce(Enum):
    DAY = 'Day'
    GTC = 'GTC'
    GTD = 'GTD'
    EXT = 'Ext'


class InstrumentType(Enum):
    EQUITY = 'Equity'
    FUTURE = 'Future'
    EQUITY_OPTION = 'Equity Option'
    FUTURE_OPTION = 'Future Option'
    CRYPTO = 'Cryptocurrency'


class OrderAction(Enum):
    BTO = 'Buy to Open'
    STO = 'Sell to Open'
    BTC = 'Buy to Close'
    STC = 'Sell to Close'


@dataclass
class Leg(object):
    """ Defines a leg of an order """
    # Minimum data to route an order
    instrument_type: InstrumentType
    symbol: str
    action: OrderAction
    quantity: Decimal = None
    # Other data when reading order back
    fills: list = None  # TODO: Fill class?
    remaining_quantity: int = None

    @classmethod
    async def parse_from_order(cls, leg: dict):
        """ Parse the leg information from API response from get_orders() """
        new_data = {
            'symbol': leg.get('symbol'),
            'instrument_type': InstrumentType(leg.get('instrument-type')),
            'quantity': leg.get('quantity'),
            'action': OrderAction(leg.get('action')),
            'fills': leg.get('fills'),
            'remaining_quantity': leg.get('remaining-quantity')
        }

        return cls(**new_data)

    async def to_order_json(self) -> dict:
        """ Transform a Leg instance into API json needed to create and route an order """
        leg_json = {
            'action': self.action.value,
            'instrument-type': self.instrument_type.value,
            'symbol': self.symbol,
            'quantity': str(self.quantity)
        }
        return leg_json

    async def is_executable(self) -> bool:
        """ Check if a leg has all the required field filled in. """
        required_data = all([
                    self.instrument_type,
                    self.symbol != '',
                    self.action,
                    self.quantity
        ])

        if not required_data:
            return False
        else:
            return True


@dataclass
class Order(object):
    """ Store data from an history order or from the response from dry-run/routing an order. """
    # Minimum data needed to place an order
    account_number: str
    type: OrderType
    time_in_force: TimeInForce
    legs: List[Leg] = field(default_factory=list)
    source: str = 'WBT'

    # Data that are not always needed to create/place an order
    id: int = None
    price: Decimal = None
    price_effect: OrderPriceEffect = None
    stop_trigger: Decimal = None
    status: OrderStatus = None
    contingent_status: str = None
    size: Decimal = None
    gtc_date: datetime = None
    underlying_symbol: str = None
    underlying_type: InstrumentType = None
    cancellable: bool = None
    editable: bool = None
    edited: bool = None
    cancelled_at: datetime = None
    received_at: datetime = None
    updated_at: datetime = None
    terminal_at: datetime = None

    # From a routed/dry-run order
    bp: dict = None
    fees: dict = None
    warnings: list = None
    errors: dict = None
    is_dry_run: bool = None

    @classmethod
    async def parse_from_api(cls, data: dict):
        """ Create a new Order from any API response related to orders (get, route, dry-run) """

        # Checking if it is a response from a routed/dry-run order (will be a nested 'order' field)
        if data.get('order'):
            order = data.get('order')
            is_routed = True
        else:
            order = data
            is_routed = False

        new_data = {
            'id': order.get('id') if order.get('id') else None,
            'account_number': order.get('account-number'),
            'time_in_force': TimeInForce(order.get('time-in-force')),
            'type': OrderType(order.get('order-type')),
            'size': order.get('size'),
            'underlying_symbol': order.get('underlying-symbol'),
            'underlying_type': InstrumentType(order.get('underlying-instrument-type')),
            'price': Decimal(order.get('price')) if order.get('price') else None,
            'price_effect': OrderPriceEffect(order.get('price-effect')) if order.get('price-effect') else None,
            'status': OrderStatus(order.get('status')),
            'contingent_status': order.get('contingent-status') if order.get('contingent-status') else None,
            'cancellable': order.get('cancellable'),
            'cancelled_at': datetime.fromisoformat(order.get('cancelled-at')) if order.get('cancelled-at') else None,
            'editable': order.get('editable'),
            'edited': order.get('edited'),
            'received_at': datetime.fromisoformat(order.get('received-at')) if order.get('received-at') else None,
            'updated_at': datetime.fromtimestamp(order.get('updated-at')/1000, tz=timezone.utc)
            if order.get('updated-at') else None,
            'terminal_at': datetime.fromisoformat(order.get('terminal-at')) if order.get('terminal-at') else None,

            'legs': [await Leg.parse_from_order(leg) for leg in order.get('legs')],
        }

        if is_routed:
            # From a routed/dry-run order only
            new_data['bp'] = data.get('buying-power-effect')
            new_data['fees'] = data.get('fee-calculation')

            if data.get('warnings') is not None:
                new_data['warnings'] = [OrderWarning(**warning) for warning in data.get('warnings')]
            if data.get('errors') is not None:
                new_data['errors'] = [OrderError(**error) for error in data.get('errors')]

        return cls(**new_data)

    async def to_order_json(self):
        """ Create the json structure needed to send to the API. """
        order_json = {
            'order-type': self.type.value,
            'source': self.source,
            'time-in-force': self.time_in_force.value,
            'legs': [await leg.to_order_json() for leg in self.legs],
            'price': '{:.2f}'.format(self.price) if self.price else 0,
            'price-effect': self.price_effect.value
        }

        if self.time_in_force is TimeInForce.GTD:
            order_json['gtc-date'] = self.gtc_date.strftime('%Y-%m-%d')

        if self.type in [OrderType.STOP_LIMIT, OrderType.STOP_MARKET]:
            order_json['stop-trigger'] = self.stop_trigger

        # TODO: Check if all the cases are covered here and check for correct value types?

        return order_json

    async def add_leg(self, leg: Leg) -> bool:
        if await leg.is_executable():
            self.legs.append(leg)
            return True
        else:
            LOGGER.error('The leg is missing some required data for routing and cannot be added to the order.')
            return False

    async def is_executable(self) -> bool:
        """ Check if an order has all the required data (does NOT check if the types of data are correct). """
        # TODO: More robust check: check that all the data types are as expected to be a valid order?

        required_data = [
            self.type,
            self.source,
            self.time_in_force,
            len(self.legs) != 0
        ]

        if self.type is not OrderType.MARKET:
            required_data.append([self.price, self.price_effect])

        if self.type in [OrderType.STOP_LIMIT, OrderType.STOP_MARKET]:
            required_data.append(self.stop_trigger)

        if self.time_in_force is TimeInForce.GTD:
            required_data.append(self.gtc_date)

        if not all(required_data):
            return False
        else:
            return True

    async def route(self, session: TastyAPISession, is_dry_run: bool = True):
        """ Route a dry-run or a real order. Update the order instance with new data from the response. """

        if not await self.is_executable():
            LOGGER.error('Order is not executable (fields may be missing or incorrect). Order was not routed.')
            return False

        order_json = await self.to_order_json()

        response = await api.route_order(session.session_token, self.account_number, order_json=order_json,
                                         is_dry_run=is_dry_run, order_id=self.id)

        # TODO: Check status here?
        # status = response.get('status')

        order_received = await Order.parse_from_api(api.get_deep_value(response, ['content', 'data']))
        order_received.is_dry_run = is_dry_run

        if is_dry_run:
            order_received.received_at = datetime.now(tz=timezone.utc)  # Not available in dry-run, adding manually here

        # Updating with new data
        await self.update_fields(order_received)

        # Check if order has been received by syncing with the live orders
        await asyncio.sleep(0.5)
        await self.live_sync(session)

        return True

    async def update(self, session: TastyAPISession):
        """ Send an updated order. """
        if not isinstance(self.id, int):
            LOGGER.error('Order does not have an ID or ID is incorrect and so order cannot be updated '
                         '(must be a dry-run).')
            return False

        if not self.editable:
            LOGGER.error('Order is not editable so it cannot be updated.')
            return False

        is_success = await self.route(session, is_dry_run=False)

        # TODO: Check if the order "updated_at" has changed or is set to confirm

        return is_success

    async def cancel(self, session: TastyAPISession) -> bool:
        """ Cancel a cancellable order. """
        if not self.id:
            LOGGER.warning('Order does not have an ID and so it cannot be cancelled (must be a dry-run).')
            return False

        is_updated = await self.live_sync(session)

        if not is_updated:
            return False

        if not self.cancellable:
            LOGGER.warning(f'Order #{self.id} is not cancellable.')
            return False

        # Cancelling an order using its 'id'
        response = await api.cancel_order(session.session_token, self.account_number, order_id=self.id)

        # Get the new order data and update the fields of our order instance
        order_received = await Order.parse_from_api(api.get_deep_value(response, ['content', 'data']))
        await self.update_fields(order_received)

        # Check if order has been received by syncing with the live orders
        await asyncio.sleep(0.5)
        await self.live_sync(session)

        return self.status == OrderStatus.CANCELLED

    async def is_received(self, session: TastyAPISession) -> bool:
        """ Verify if an order is Received by updating it from the list of live orders and then checking its status. """
        await self.live_sync(session)
        return self.status == OrderStatus.RECEIVED

    async def is_live(self, session: TastyAPISession) -> bool:
        """ Verify if an order is live by updating it from the list of live orders and then checking its status. """
        await self.live_sync(session)
        return self.status == OrderStatus.LIVE

    async def live_sync(self, session: TastyAPISession):
        """ Update self order instance with the data from a live orders if found by matching IDs. """
        if not self.id:
            LOGGER.error('Order has no ID and so it cannot be synced with live orders.')
            return False

        response = await api.get_orders_live(session.session_token, self.account_number)
        items = api.get_deep_value(response, ['content', 'data', 'items'])

        match = [order for order in items if order.get('id') == self.id]

        if len(match) == 0:
            LOGGER.error(f'Order ID was not found in the list of live orders. It may not be live or is a dry-run. '
                         f'The order cannot be synced with live orders.')
            return False
        elif len(match) > 1:
            LOGGER.error('Something went wrong. Found multiple matching orders. Should be only one.')
            return False

        # Updating the existing order fields
        order = await Order.parse_from_api(match[0])
        await self.update_fields(order)

        # Hack to remove the contingent value once an order is live (pending better update_fields() method)
        if self.status == OrderStatus.LIVE:
            self.contingent_status = ''

        return True

    async def update_fields(self, newer_order):
        """ Updating the fields is they are different and not None in the newer order. """
        # TODO: This may need a smarter way to get it done to process fields better? (some set to None we may want)
        for k, v in vars(newer_order).items():
            if v != getattr(self, k) and v is not None:
                setattr(self, k, v)

        return self

    async def total_fees(self) -> Decimal:
        """ Return the total of the fees with the sign in a Decimal. """
        fees = Decimal(self.fees.get('total-fees'))*OrderPriceEffectSign[self.fees.get('total-fees-effect')].value
        return fees

    async def do_50_pop(self):
        """ Run the 50% POP simulation. """
        # TODO: Implement this if it can be useful
        pass
