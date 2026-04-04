import os

import classes.IThread
import classes.IUser


def test_get_thread_by_id(session_fixture):
    result = classes.IThread.IThread.from_id(os.getenv("TESTS_THREADID"), handler=session_fixture)

    # The result is either a Thread or None
    assert isinstance(result, classes.IThread.IThread) or isinstance(result, type(None))

    # If the result isn't None, verify it has extra fields
    if result is not None:
        assert hasattr(result, "members")
        assert result.members is not None
        assert isinstance(result.members, list)
        assert len(result.members) > 0
        assert isinstance(result.members[0], classes.IUser.IUser)
