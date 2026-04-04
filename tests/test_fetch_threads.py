import classes.IThread


def test_fetch_threads(session_fixture):
    result = classes.IThread.fetch_threads(handler=session_fixture)

    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], classes.IThread.IThread)
