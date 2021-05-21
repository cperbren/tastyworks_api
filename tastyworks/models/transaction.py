import logging

from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

LOGGER = logging.getLogger(__name__)


@dataclass
class Transaction(object):
    # Data present in all types of transactions
    id: int
    account_number: str
    type: str
    sub_type: str
    executed_at: datetime
    value: Decimal
    value_effect: str
    net_value: Decimal
    net_value_effect: str
    # Raw data from the API
    details: dict
    # Data that are sometimes not present depending on the type of transaction
    symbol: str = None
    underlying: str = None
    action: str = None
    quantity: Decimal = None
    price: Decimal = None
    fees: Decimal = None
    order_id: int = None

    @classmethod
    async def parse_from_api(cls, tr: dict):
        """
        Create a new Transaction from API response
        """
        new_data = {
            # Data found in all types of transactions
            'id': tr.get('id'),
            'account_number': tr.get('account-number'),
            'type': tr.get('transaction-type'),
            'sub_type': tr.get('transaction-sub-type'),
            'executed_at': datetime.fromisoformat(tr.get('executed-at')),
            'value': Decimal(tr.get('value')),
            'value_effect': tr.get('value-effect'),
            'net_value': Decimal(tr.get('net-value')),
            'net_value_effect': tr.get('net-value-effect'),
            # Raw data from the API
            'details': tr,
            # Data that are sometimes not present
            'symbol': tr.get('symbol'),
            'order_id': tr.get('order-id'),
            'underlying': tr.get('underlying-symbol'),
            'action': tr.get('action'),
            'quantity': Decimal(tr.get('quantity')) if tr.get('quantity') else None,
            'price': Decimal(tr.get('price')) if tr.get('price') else None,
            'fees': Decimal(tr.get('regulatory-fees') if tr.get('regulatory-fees') else 0) +
                    Decimal(tr.get('clearing-fees') if tr.get('clearing-fees') else 0) +
                    Decimal(tr.get('commission') if tr.get('commission') else 0)
        }

        res = cls(**new_data)

        return res
