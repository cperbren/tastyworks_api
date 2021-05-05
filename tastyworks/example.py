import asyncio
import calendar
import logging
from os import environ
from datetime import date, timedelta
from decimal import Decimal

from tastyworks.models import option_chain, underlying
from tastyworks.models.option import Option, OptionType
from tastyworks.models.order import (Order, OrderDetails, OrderPriceEffect,
                                     OrderType)
from tastyworks.models.session import TastyAPISession
from tastyworks.models.trading_account import TradingAccount
from tastyworks.models.underlying import UnderlyingType
from tastyworks.streamer import DataStreamer
from tastyworks.tastyworks_api import tasty_session

LOGGER = logging.getLogger(__name__)


async def main_loop(session: TastyAPISession, streamer: DataStreamer):

    accounts = await TradingAccount.get_remote_accounts(session)
    acct = accounts[1]
    LOGGER.info('Accounts available: %s', accounts)

    orders = await Order.get_remote_orders(session, acct)
    LOGGER.info('Number of active orders: %s', len(orders))

    # Execute an order

    details = OrderDetails(
        type=OrderType.LIMIT,
        price=Decimal(400),
        price_effect=OrderPriceEffect.CREDIT)
    new_order = Order(details)

    opt = Option(
        ticker='SPY',
        quantity=1,
        expiry=get_third_friday(date.today()),
        strike=Decimal(400),
        option_type=OptionType.CALL,
        underlying_type=UnderlyingType.EQUITY
    )
    new_order.add_leg(opt)

    res = await acct.execute_order(new_order, session, dry_run=True)
    LOGGER.info('Order executed successfully: %s', res)

    # Get an options chain
    undl = underlying.Underlying('SPY')

    chain = await option_chain.get_option_chain(session, undl)
    LOGGER.info('Chain strikes: %s', chain.get_all_strikes())

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
