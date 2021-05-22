import logging

from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

LOGGER = logging.getLogger(__name__)


@dataclass
class Position(object):
    # Data present in all types of transactions
    account_number: str
    symbol: str
    instrument_type: str
    underlying_symbol: str
    quantity: Decimal
    quantity_direction: str
    close_price: Decimal
    open_price: Decimal
    multiplier: Decimal
    cost_effect: str
    created_at: datetime
    # Raw data from the API
    details: dict
    # Data that are sometimes not present depending on the type of position
    expires_at: datetime = None
    updated_at: datetime = None

    @classmethod
    async def parse_from_api(cls, pos: dict):
        """
        Create a new Transaction from API response
        """
        new_data = {
            'account_number': pos.get('account-number'),
            'symbol': pos.get('symbol'),
            'instrument_type': pos.get('instrument-type'),
            'underlying_symbol': pos.get('underlying-symbol'),
            'quantity': Decimal(pos.get('quantity')),
            'quantity_direction': pos.get('quantity-direction'),
            'close_price': Decimal(pos.get('close-price')) if pos.get('close-price') else None,
            'open_price': Decimal(pos.get('average-open-price')) if pos.get('average-open-price') else None,
            'multiplier': Decimal(pos.get('multiplier')) if pos.get('multiplier') else None,
            'cost_effect': pos.get('cost-effect'),
            'created_at': datetime.fromisoformat(pos.get('created-at')) if pos.get('created-at') else None,
            'expires_at': datetime.fromisoformat(pos.get('expires-at')) if pos.get('expires-at') else None,
            'updated_at': datetime.fromisoformat(pos.get('updated-at')) if pos.get('updated-at') else None,
            'details': pos
        }

        return cls(**new_data)
