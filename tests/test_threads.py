import datetime

import classes.IMessage
from classes import IThread, IUser


class TestRequestHandler:
    def test_fetch_threads(self, session_fixture):
        result = IThread.fetch_threads(handler=session_fixture)

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], IThread.IThread)

    def test_get_thread_by_id(self, session_fixture):
        result = IThread.IThread.from_id(340282366841710301244260043370061655929, handler=session_fixture)

        # The result is either a Thread or None
        assert isinstance(result, IThread.IThread) or isinstance(result, type(None))

        # If the result isn't None, verify it has extra fields
        if result is not None:
            assert hasattr(result, "members")
            assert result.members is not None
            assert isinstance(result.members, list)
            assert len(result.members) > 0
            assert isinstance(result.members[0], IUser.IUser)

    def test_get_messages(self, session_fixture):
        thread = IThread.IThread.from_id(340282366841710301244260043370061655929, handler=session_fixture)
        if thread is None:
            return self.test_get_messages(session_fixture)

        messages = thread.fetch_messages(limit_date=datetime.datetime.fromtimestamp(1775062800), handler=session_fixture)

        assert isinstance(messages, list)
        assert len(messages) > 0
        assert isinstance(messages[0], classes.IMessage.IMessage)

        return None
