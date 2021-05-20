from typing import List

from datetime import date
from dataclasses import dataclass
import tastyworks.tastyworks_api.tw_api as api

from tastyworks.models.order import Order, OrderPriceEffect


@dataclass
class TradingAccount(object):
    account_number: str
    details: dict = None
    balances: dict = None
    status: dict = None
    capital_req: dict = None
    underlyings: list = None
    positions: list = None
    orders: list = None
    orders_live: list = None
    transactions: list = None

    @classmethod
    async def get_accounts(cls, session) -> List:
        """
        Gets all trading accounts from the Tastyworks platform from an active session.

        Args:
            session (TastyAPISession): An active and logged-in session object against which to query.

        Returns:
            list (TradingAccount): A list of trading accounts.
        """
        res = []
        response = await api.get_accounts(session.session_token)

        data = api.get_deep_value(response, ['content', 'data', 'items'])

        for entry in data:
            # if entry.get('authority-level') != 'owner':
            #     continue
            acct_data = entry.get('account')
            acct = TradingAccount._parse_from_api(acct_data)
            res.append(acct)

        return res

    async def execute_order(self, order: Order, session, dry_run=True):
        """
        Execute an order. If doing a dry run, the order isn't placed but simulated (server-side).

        Args:
            order (Order): The order object to execute.
            session (TastyAPISession): The tastyworks session onto which to execute the order.
            dry_run (bool): Whether to do a test (dry) run.

        Returns:
            bool: Whether the order was successful.
        """
        if not order.check_is_order_executable():
            raise Exception('Order is not executable, most likely due to missing data')

        if not await session.is_active():
            raise Exception('The supplied session is not active and valid')

        body = _get_execute_order_json(order)

        resp = await api.route_order(session.session_token, self.account_number, order_json=body, is_dry_run=dry_run)

        if resp.get('status') == 201:
            return True
        elif resp.get('status') == 400:
            raise Exception(f'Order execution failed, message: {resp.get("reason")}')
        else:
            raise Exception(f'Unknown remote error, status code: {resp.get("reason")}, message: {resp.get("reason")}')

    @classmethod
    def _parse_from_api(cls, data: dict):
        """
        Parses a TradingAccount object from an API dict response.
        """
        new_data = {
            'account_number': data.get('account-number'),
            'details': data
        }

        res = TradingAccount(**new_data)

        return res

    async def get_everything(self, session):
        """
        Get all the account information at once using default counts for orders (200) & transactions (2000).
        """
        await self.get_balances(session)
        await self.get_status(session)
        await self.get_capital_req(session)
        await self.get_underlyings(session)
        await self.get_positions(session)
        self.orders = await self.get_orders(session)
        self.orders_live = await self.get_orders_live(session)
        self.transactions = await self.get_transactions(session)

        return True

    async def get_balances(self, session):
        """
        Get account balances.

        Args:
            session (TastyAPISession): An active and logged-in session object against which to query.
        Returns:
            dict: account attributes
        """
        response = await api.get_balances(session.session_token, self.account_number)

        self.balances = api.get_deep_value(response, ['content', 'data'])

        return self.balances

    async def get_status(self, session):
        """
        Get the status of the account
        """
        response = await api.get_status(session.session_token, self.account_number)

        self.status = api.get_deep_value(response, ['content', 'data'])

        return self.status

    async def get_capital_req(self, session):
        """
        Get the capital requirement of the account
        """
        response = await api.get_capital_req(session.session_token, self.account_number)

        self.capital_req = api.get_deep_value(response, ['content', 'data'])

        return self.capital_req

    async def get_underlyings(self, session):
        """
        Get the active underlyings of an account
        """
        response = await api.get_capital_req(session.session_token, self.account_number)

        self.underlyings = api.get_deep_value(response, ['content', 'data', 'underlyings'])
        # TODO: Use an "Underlying" class?

        return self.underlyings

    async def get_positions(self, session):
        """
        Get Open Positions.
        """
        response = await api.get_positions(session.session_token, self.account_number)

        self.positions = api.get_deep_value(response, ['content', 'data', 'items'])
        # TODO: Use a "Position" class

        return self.positions

    async def get_orders(self, session, symbol: str = '',
                         start_date: date = None, end_date: date = None,
                         per_page: int = 200, page_number: int = 1):
        """
        Get all orders current and past with optional pagination.

        Args:
            session (TastyAPISession): An active and logged-in session object against which to query.
            symbol
            start_date
            end_date
            per_page
            page_number
        Returns:
            A list of orders matching the sorting criteria
        """
        response = await api.get_orders(session.session_token, self.account_number, symbol=symbol,
                                        start_date=start_date, end_date=end_date,
                                        per_page=per_page, page_number=page_number)
        # TODO: Use the Order class
        orders = api.get_deep_value(response, ['content', 'data', 'items'])

        return orders

    async def get_orders_live(self, session):
        """
        Get live open orders.
        """
        response = await api.get_orders_live(session.session_token, self.account_number)

        self.orders_live = api.get_deep_value(response, ['content', 'data', 'items'])
        # TODO: Use the Order class

        return self.orders_live

    async def get_transactions(self, session, symbol: str = '',
                               start_date: date = None, end_date: date = None,
                               per_page: int = 2000, page_number: int = 1):
        """
        Get past transactions.
        """
        response = await api.get_transactions(session.session_token, self.account_number, symbol=symbol,
                                              start_date=start_date, end_date=end_date,
                                              per_page=per_page, page_number=page_number)

        transactions = api.get_deep_value(response, ['content', 'data', 'items'])
        # TODO: Use a Transaction class (to be added)

        return transactions


# TODO: MOVE THIS SOMEWHERE ELSE BETTER ?
def _get_execute_order_json(order: Order):
    order_json = {
        'source': order.details.source,
        'order-type': order.details.type.value,
        'price': '{:.2f}'.format(order.details.price),
        'price-effect': order.details.price_effect.value,
        'time-in-force': order.details.time_in_force.value,
        'legs': _get_legs_request_data(order)
    }

    if order.details.gtc_date:
        order_json['gtc-date'] = order.details.gtc_date.strftime('%Y-%m-%d')

    return order_json


# TODO: MOVE THIS SOMEWHERE ELSE BETTER ?
def _get_legs_request_data(order):
    res = []
    order_effect = order.details.price_effect
    order_effect_str = 'Sell to Open' if order_effect == OrderPriceEffect.CREDIT else 'Buy to Open'
    for leg in order.details.legs:
        leg_dict = {**leg.to_tasty_json(), 'action': order_effect_str}
        res.append(leg_dict)
    return res
