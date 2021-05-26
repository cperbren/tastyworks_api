import asyncio
import calendar
import logging
from os import environ
from datetime import date, timedelta
from decimal import Decimal

from tastyworks.tastyworks_api.session import TastyAPISession
from tastyworks.streamer import DataStreamer
from tastyworks.models.account import Account
from tastyworks.models.order import Leg, Order, OrderType, TimeInForce, InstrumentType, OrderAction, OrderPriceEffect

LOGGER = logging.getLogger(__name__)


async def main_loop(session: TastyAPISession, streamer: DataStreamer):
    """ Example usage of classes and methods. """

    """
    #################
    # ACCOUNT STUFF #
    #################
    """
    # Getting account with 'owner' status >> YOU MAY NEED TO CHANGE THE ACCOUNT CHOICE BELOW
    accounts = await Account.get_accounts(session)
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

    # Get the underlyings present for open position in an account
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

    # Get all the "live" orders (today's orders active, routed, cancelled)
    orders_live = await acct.get_orders_live(session)
    LOGGER.info(f'Number of orders active/executed/cancelled today: {len(orders_live)}')

    # Get all the accounts information at once [includes 200 orders & 2000 transactions]
    await acct.get_everything(session)
    LOGGER.info(f'Number of past transactions: {len(acct.transactions)}')

    """
    ################
    # TRANSACTIONS #
    ################
    """

    # Get past transactions (default last 2,000 transactions)
    acct.transactions = await acct.get_transactions(session)
    LOGGER.info(f'Number of past transactions: {len(acct.transactions)}')

    # Another example: fetching transactions with extra filters and pagination
    symbol = 'SPY'
    days = 90
    start_date = date.today() - timedelta(days=days)  # last 90 days
    end_date = date.today()
    acct.transactions = await acct.get_transactions(session, symbol=symbol, start_date=start_date, end_date=end_date,
                                                    per_page=10, page_number=1)
    LOGGER.info(f'Number of past {symbol} transactions for the last {days} days: {len(acct.transactions)}')

    """
    ##################
    # READING ORDERS #
    ##################
    """

    # Similar to the transactions, another example: fetching orders with extra filters and pagination
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

    # Creating the leg(s) first
    leg = Leg(
        action=OrderAction.BTO,
        instrument_type=InstrumentType.EQUITY,
        quantity=Decimal(1),
        symbol='SPY'
    )

    # Creating the order and adding the leg(s)
    order = Order(
        account_number=acct.account_number,
        type=OrderType.LIMIT,
        price=Decimal(100),
        price_effect=OrderPriceEffect.DEBIT,
        time_in_force=TimeInForce.DAY,
    )
    await order.add_leg(leg)

    # Route a dry-run order (order instance is updated with new response), check the fees.
    is_success = await order.route(session, is_dry_run=True)
    fees = await order.total_fees()
    LOGGER.info(f'Order dry-run {"successful" if is_success else "failed"}. Fees are: {fees}.')

    # Check for errors and warnings
    LOGGER.info(f'Dry-Run order has {len(order.errors) if order.errors else 0} error(s) and '
                f'{len(order.warnings) if order.warnings else 0} warning(s).')

    # Try to update and cancel a dry-run order (should return some error message in the log because no ID)
    await order.update(session)
    await order.cancel(session)

    # Route a real order (order instance is updated with new response)
    is_success = await order.route(session, is_dry_run=False)
    fees = await order.total_fees()
    LOGGER.info(f'Order #{order.id} {"not " if not is_success else ""}routed. Fees are: {fees}.')
    LOGGER.info(f'Order has {len(order.errors) if order.errors else 0} error(s) and '
                f'{len(order.warnings) if order.warnings else 0} warning(s).')

    # Modifying a live order (order instance is updated with new response) - Note: Cannot update a dry-run (no ID)
    order.price = Decimal(101.50)
    order.time_in_force = TimeInForce.GTD
    is_success = await order.update(session)
    LOGGER.info(f'Order #{order.id} was {"not " if not is_success else ""}modified.')

    # Cancel the order and update its values (order instance is updated with new response data)
    is_success = await order.cancel(session)
    if is_success:
        LOGGER.info(f'Order #{order.id}: {order.status.value} '
                    f'at {order.cancelled_at.strftime("%m/%d/%Y %H:%M:%S-%f")}')

    await order.live_sync(session)
    LOGGER.info(f'Order')

    """
    ################
    # TRADING DATA #
    ################
    """

    # TODO

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
    ##########
    # ALERTS #
    ##########
    """

    # TODO

    """
    ############
    # STREAMER #
    ############
    """
    sub_values = {
        'Quote': ['SPY']
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

    # Creating a new blank TW API session and start it using environment variables
    tw_session = TastyAPISession()
    await tw_session.start(environ.get('TW_USER', ""), environ.get('TW_PASSWORD', ""))

    # Creating a new Data Streamer connection
    streamer = await DataStreamer.start(tw_session)

    # LOGGER.info('Streamer token: %s' % streamer.get_streamer_token())
    try:
        # await main_loop(tw_session, streamer)
        await main_loop(tw_session, streamer)
    finally:
        # This is not working
        await streamer.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
