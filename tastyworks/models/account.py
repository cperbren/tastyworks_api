from typing import List

from datetime import date
from dataclasses import dataclass
import tastyworks.tastyworks_api.tw_api as api

from tastyworks.models.session import TastyAPISession
from tastyworks.models.transaction import Transaction
from tastyworks.models.position import Position
from tastyworks.models.order import Order


@dataclass
class Account(object):
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
    async def get_accounts(cls, session: TastyAPISession) -> List:
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
            acct = await Account._parse_from_api(acct_data)
            res.append(acct)

        return res

    @classmethod
    async def _parse_from_api(cls, data: dict):
        """
        Parses a TradingAccount object from an API dict response.
        """
        new_data = {
            'account_number': data.get('account-number'),
            'details': data
        }

        res = Account(**new_data)

        return res

    async def get_everything(self, session: TastyAPISession):
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

    async def get_balances(self, session: TastyAPISession):
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

    async def get_status(self, session: TastyAPISession):
        """
        Get the status of the account
        """
        response = await api.get_status(session.session_token, self.account_number)

        self.status = api.get_deep_value(response, ['content', 'data'])

        return self.status

    async def get_capital_req(self, session: TastyAPISession):
        """
        Get the capital requirement of the account
        """
        response = await api.get_capital_req(session.session_token, self.account_number)

        self.capital_req = api.get_deep_value(response, ['content', 'data'])

        return self.capital_req

    async def get_underlyings(self, session: TastyAPISession):
        """
        Get the active underlyings of an account
        """
        response = await api.get_capital_req(session.session_token, self.account_number)

        self.underlyings = api.get_deep_value(response, ['content', 'data', 'underlyings'])
        # TODO: Use an "Underlying" class?

        return self.underlyings

    async def get_positions(self, session: TastyAPISession):
        """
        Get Open Positions.
        """
        response = await api.get_positions(session.session_token, self.account_number)

        items = api.get_deep_value(response, ['content', 'data', 'items'])

        self.positions = []
        for entry in items:
            position = await Position.parse_from_api(entry)
            self.positions.append(position)

        return self.positions

    async def get_orders(self, session: TastyAPISession, symbol: str = '',
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
            A list of orders matching the sorting criteria. Not assigning to the class instance
            to prevent overwriting of user data
        """
        response = await api.get_orders(session.session_token, self.account_number,
                                        symbol=symbol,
                                        start_date=start_date, end_date=end_date,
                                        per_page=per_page, page_number=page_number)

        items = api.get_deep_value(response, ['content', 'data', 'items'])

        orders = []
        for entry in items:
            order = await Order.parse_from_api(entry)
            orders.append(order)

        return orders

    async def get_orders_live(self, session: TastyAPISession):
        """
        Get live open orders.
        """
        response = await api.get_orders_live(session.session_token, self.account_number)

        items = api.get_deep_value(response, ['content', 'data', 'items'])

        self.orders_live = []
        for entry in items:
            order = await Order.parse_from_api(entry)
            self.orders_live.append(order)

        return self.orders_live

    async def get_transactions(self, session: TastyAPISession, symbol: str = '',
                               start_date: date = None, end_date: date = None,
                               per_page: int = 2000, page_number: int = 1) -> List:
        """
        Get past transactions. Not assigning to the class instance to prevent overwriting of user data
        """
        response = await api.get_transactions(session.session_token, self.account_number, symbol=symbol,
                                              start_date=start_date, end_date=end_date,
                                              per_page=per_page, page_number=page_number)

        items = api.get_deep_value(response, ['content', 'data', 'items'])

        transactions = []
        for entry in items:
            transaction = await Transaction.parse_from_api(entry)
            transactions.append(transaction)

        return transactions

    # async def execute_order(self, order: Order, session, dry_run=True):
    #     """
    #     Execute an order. If doing a dry run, the order isn't placed but simulated (server-side).
    #
    #     Args:
    #         order (Order): The order object to execute.
    #         session (TastyAPISession): The tastyworks session onto which to execute the order.
    #         dry_run (bool): Whether to do a test (dry) run.
    #
    #     Returns:
    #         bool: Whether the order was successful.
    #     """
    #     if not order.check_is_order_executable():
    #         raise Exception('Order is not executable, most likely due to missing data')
    #
    #     if not await session.is_active():
    #         raise Exception('The supplied session is not active and valid')
    #
    #     body = _get_execute_order_json(order)
    #
    #     resp = await api.route_order(session.session_token, self.account_number, order_json=body, is_dry_run=dry_run)
    #
    #     if resp.get('status') == 201:
    #         return True
    #     elif resp.get('status') == 400:
    #         raise Exception(f'Order execution failed, message: {resp.get("reason")}')
    #     else:
    #         raise Exception(f'Unknown remote error, status code: {resp.get("reason")}, message: {resp.get("reason")}')
