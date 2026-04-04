import os

import classes.IMessage
import classes.IThread

tries: int = 1


def test_get_messages(session_fixture):
    global tries

    thread = classes.IThread.IThread.from_id(os.getenv("TESTS_THREADID"), handler=session_fixture)
    if thread is None:
        if tries > 10:
            raise Exception("Failed to get thread after 10 tries")

        tries += 1
        return test_get_messages(session_fixture)

    messages = thread.fetch_messages(handler=session_fixture)

    assert isinstance(messages, list)
    assert len(messages) > 0
    assert isinstance(messages[0], classes.IMessage.IMessage)

    return None
