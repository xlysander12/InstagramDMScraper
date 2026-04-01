from dotenv import load_dotenv
import pytest
import os
import sys

import utils.request_handler

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
load_dotenv()

@pytest.fixture
def session_fixture():
    sessionid = os.getenv("SESSIONID")
    if not sessionid:
        pytest.fail("SESSION_ID environment variable not set")

    # Set the session in the var
    utils.request_handler.set_sessionid(sessionid)
    print("Session ID set for tests")

    # Return the module
    return utils.request_handler