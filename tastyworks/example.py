import asyncio
import calendar
import logging
from os import environ
from datetime import date, timedelta
from decimal import Decimal

from tastyworks.models import option_chain, underlying
from tastyworks.models.option import Option, OptionType
from tastyworks.models.order import (Order, OrderDetails, OrderPriceEffect,OrderType)
from tastyworks.models.session import TastyAPISession
from tastyworks.models.account import TradingAccount
from tastyworks.models.underlying import UnderlyingType
from tastyworks.streamer import DataStreamer
from tastyworks.tastyworks_api import tasty_session

LOGGER = logging.getLogger(__name__)


async def main_loop(session: TastyAPISession, streamer: DataStreamer):
    """
        Example usage of classes and methods
    """

    """
    #################
    # ACCOUNT STUFF #
    #################
    """
    # Getting account with 'owner' status >> YOU MAY NEED TO CHANGE THE ACCOUNT CHOICE BELOW
    accounts = await TradingAccount.get_accounts(session)
    acct = accounts[2]
    LOGGER.info('Accounts available: %s', accounts)

    # Getting an account balances
    balances = await acct.get_balances(session)
    LOGGER.info(f'Account balances: \n'
                f'Cash Balance: ${balances.get("cash-balance")}\n'
                f'Margin Equity: ${balances.get("margin-equity")}')

    # Get the status of an account
    status = await acct.get_status(session)
    LOGGER.info(f'Account status: \n'
                f'Is it closed? {status.get("is-closed")}\n'
                f'Options level: {status.get("options-level")}')

    # Get the margin/capital requirements of an account
    # Also a way to getting all the current positions, orders, legs, etc. in the account with extra details
    capital = await acct.get_capital_req(session)
    LOGGER.info(f'Account capital requirements: \n'
                f'Margin requirement: ${capital.get("margin-requirement")}\n'
                f'Option buying power: ${capital.get("reg-t-option-buying-power")}')

    underlyings = await acct.get_underlyings(session)
    LOGGER.info(f'Account holding details: \n'
                f'Underlyings list: {[underlyings[n].get("code") for n in range(len(underlyings))]}\n'
                f'Open Orders IDs: ${[underlyings[n].get("order-ids") for n in range(len(underlyings))]}')

    # Get all the open positions for an account
    positions = await acct.get_positions(session)
    LOGGER.info('Number of active positions: %s', len(positions))

    # Get the open and past orders (default last 200 orders) - See details for sorting and pagination
    orders = await acct.get_orders(session)
    LOGGER.info(f'Number of past orders retrieved: {len(orders)}')

    # Get all the live orders (today's orders)
    orders_live = await acct.get_orders_live(session)
    LOGGER.info(f'Number of active orders: {len(orders_live)}')

    # Get past transactions (default last 2000 transactions) - See details for sorting and pagination
    transactions = await acct.get_transactions(session)
    LOGGER.info(f'Number of past transactions: {len(transactions)}')

    # Get all the accounts information at once [includes 200 orders & 2000 transactions]
    await acct.get_everything(session)
    LOGGER.info(f'Number of past transactions: {len(acct.transactions)}')

    """
    ##############
    # WATCHLISTS #
    ##############
    """

    # TODO: Update the Watchlist class

    """
    ###########
    # JOURNAL #
    ###########
    """

    # TODO: Need to create a Journal (maybe) and/or JournalEntry classes

    """
    ##################
    # READING ORDERS #
    ##################
    """

    # Similar to the account section, here you can fetch orders with extra filters
    symbol = 'SPY'
    start_date = date.today() - timedelta(days=90)  # last 90 days
    end_date = date.today()
    orders = await acct.get_orders(session, symbol=symbol, start_date=start_date, end_date=end_date,
                                   per_page=10, page_number=1)
    LOGGER.info(f'Last 10 active orders for the past 90 days for SPY: {[orders[n] for n in range(len(orders))]}')

    """
    ##################
    # ROUTING ORDERS #
    ##################
    """

    # TODO

    """
    ################
    # TRANSACTIONS #
    ################
    """

    # TODO

    """
    ################
    # TRADING DATA #
    ################
    """

    # TODO

    """
    ##########
    # ALERTS #
    ##########
    """

    # TODO




    #
    # # Execute an order
    #
    # details = OrderDetails(
    #     type=OrderType.LIMIT,
    #     price=Decimal(400),
    #     price_effect=OrderPriceEffect.CREDIT)
    # new_order = Order(details)
    #
    # opt = Option(
    #     ticker='SPY',
    #     quantity=1,
    #     expiry=get_third_friday(date.today()),
    #     strike=Decimal(400),
    #     option_type=OptionType.CALL,
    #     underlying_type=UnderlyingType.EQUITY
    # )
    # new_order.add_leg(opt)
    #
    # res = await acct.execute_order(new_order, session, dry_run=True)
    # LOGGER.info('Order executed successfully: %s', res)
    #
    # # Get an options chain
    # undl = underlying.Underlying('SPY')
    #
    # chain = await option_chain.get_option_chain(session, undl)
    # LOGGER.info('Chain strikes: %s', chain.get_all_strikes())

    sub_values = {
        "Quote": ["/ES"]
    }
    await streamer.add_data_sub(sub_values)

    async for item in streamer.listen():
        LOGGER.info('Received item: %s' % item.data)


def get_third_friday(d):
    s = date(d.year, d.month, 15)
    candidate = s + timedelta(days=(calendar.FRIDAY - s.weekday()) % 7)

    # This month's third friday passed
    if candidate < d:
        candidate += timedelta(weeks=4)
        if candidate.day < 15:
            candidate += timedelta(weeks=1)

    return candidate


async def main():

    # Creating a new TW API session using async and the new API abstraction layer
    tw_session = await TastyAPISession.start(environ.get('TW_USER', ""), environ.get('TW_PASSWORD', ""))

    # Creating a new Data Streamer connection
    streamer = await DataStreamer.start(tw_session)

    # LOGGER.info('Streamer token: %s' % streamer.get_streamer_token())
    try:
        await main_loop(tw_session, streamer)
    finally:
        # This is not working
        await streamer.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
