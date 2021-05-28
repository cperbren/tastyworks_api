import logging
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta, date


import tastyworks.tastyworks_api.tw_api as api
from tastyworks.tastyworks_api.session import TastyAPISession


LOGGER = logging.getLogger(__name__)


class UnderlyingType(Enum):
    EQUITY = 'Equity'
    FUTURE = 'Future'
    # STOCK = 'Stock'
    # INDEX = 'Index'
    # BOND = 'Bond'
    # WARRANT = 'Warrant'
    # CRYPTO = 'Crypto'


@dataclass
class Dividend(object):
    div_rate_per_share: Decimal = None
    div_yield: Decimal = None
    div_per_year: Decimal = None
    ex_date: date = None
    next_date: date = None
    pay_date: date = None
    updated_at: datetime = None


@dataclass
class Earnings(object):
    pass


@dataclass
class Underlying(object):
    symbol: str
    description: str = None

    iv_rank: Decimal = None
    iv_index: Decimal = None
    beta: Decimal = None
    corr_spy: Decimal = None
    liquidity_rating: int = None

    # Dividends & Earnings
    dividend: Dividend = None
    earnings: dict = None  # Earnings = None

    # Last update of the market metrics
    metrics_updated_at: datetime = None

    # Price data
    bid: Decimal = None
    ask: Decimal = None
    quote_updated_at: datetime = None
    open: Decimal = None
    high: Decimal = None
    low: Decimal = None
    close: Decimal = None
    ohlc_timeframe: timedelta = None

    # All raw API data
    details: dict = None

    @classmethod
    async def from_metrics(cls, session: TastyAPISession, symbols):
        """
        Args:
            session: an open TastyAPISession session
            symbols: a string for one symbol or a list of strings for multiple symbols metrics query at once
        Returns:

        An Underlying instance or a list of Underlying with data retrieved using the API market metrics request
        (volatility, beta, dividends, earnings, etc.).
        """

        items = await get_metrics(session, symbols)

        # If the symbol or symbols passed cannot be found and the API call returns an empty response
        if items is None:
            return None

        underlyings = []
        for metrics in items:
            undl = cls(symbol=metrics.get('symbol'))
            await undl.update_metrics(metrics)
            await undl.update_dividend(metrics)
            underlyings.append(undl)

        return underlyings[0] if len(underlyings) == 1 else underlyings

    async def update_metrics(self, metrics):
        metrics_data = {
            'symbol': metrics.get('symbol'),
            'iv_rank': metrics.get('implied-volatility-index-rank'),
            'iv_index': metrics.get('implied-volatility-index'),
            'beta': metrics.get('beta'),
            'corr_spy': metrics.get('corr-spy-3month'),
            'liquidity_rating': metrics.get('liquidity-rating'),
            'earnings': metrics.get('earnings'),
            'metrics_updated_at': datetime.now(),
            'details': metrics
        }
        for key, value in metrics_data.items():
            setattr(self, key, value)

        return self

    async def update_dividend(self, metrics):
        if not metrics.get('dividend-updated-at'):
            updated_at = None
        elif len(metrics.get('dividend-updated-at')) == 29:
            updated_at = datetime.fromisoformat(metrics.get('dividend-updated-at'))
        elif len(metrics.get('dividend-updated-at')) == 24:
            updated_at = datetime.strptime(metrics.get('dividend-updated-at')[:-1] + '000', '%Y-%m-%dT%H:%M:%S.%f')
        else:
            LOGGER.error('Dividend update date could not be read properly. Not updated.')
            updated_at = None

        div_data = {
            'div_rate_per_share': Decimal(metrics.get('dividend-rate-per-share')) if metrics.get('dividend-rate-per-share') else None,
            'div_yield': Decimal(metrics.get('dividend-yield')) if metrics.get('dividend-yield') else None,
            'div_per_year': Decimal(metrics.get('annual-dividend-per-share')) if metrics.get('annual-dividend-per-share') else None,
            'ex_date': date.fromisoformat(metrics.get('dividend-ex-date')) if metrics.get('dividend-ex-date') else None,
            'next_date': date.fromisoformat(metrics.get('dividend-next-date')) if metrics.get('dividend-next-date') else None,
            'pay_date': date.fromisoformat(metrics.get('dividend-pay-date')) if metrics.get('dividend-pay-date') else None,
            'updated_at': updated_at
        }
        self.dividend = Dividend(**div_data)

        return self


async def search_symbol(session: TastyAPISession, string: str):
    """
    Performs a symbol search using Tastyworks API.

    This returns a list of 20 symbols that are similar to the symbol passed in
    the parameters. This does not provide any details except the related
    symbols and their descriptions.

    Args:
        session (TastyAPISession): Aan open TW API session with valid token
        string (str): A string to search for symbols starting with

    Returns:
        underlyings (list): A list of Underlying
    """
    response = await api.symbol_search(session.session_token, string)

    items = api.get_deep_value(response, ['content', 'data', 'items'])

    underlyings = [Underlying(**item) for item in items]

    return underlyings


async def get_metrics(session: TastyAPISession, symbols):
    """ Return a list of metrics from the input symbols. Will not return an item is a symbol is not found. """
    if isinstance(symbols, str):
        symbols = [symbols]

    # Removing the ':' from symbols even though it doesn't return anything for future proof
    symbols_cleaned = [symbol.replace(':', '') for symbol in symbols]

    response = await api.get_market_metrics(session.session_token, symbols_cleaned)
    items = api.get_deep_value(response, ['content', 'data', 'items'])

    return items
