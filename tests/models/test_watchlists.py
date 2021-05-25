from tastyworks.models.watchlists import WatchlistGroup
from tastyworks.models.session import TastyAPISession
import asyncio


class TestWatchlists(object):
    """Test Watchlists

    Class to test watchlist groups and watchlists.

    Args:
        username (string): Tastyworks username
        password (string): Tastyworks password
    """

    def __init__(self, username: str, password: str, public: bool = True):
        self.session = TastyAPISession.start(username, password)
        self.watchlists = asyncio.run(
            WatchlistGroup.get_watchlists(self.session, public=public)  # NOQA: E501
        )
