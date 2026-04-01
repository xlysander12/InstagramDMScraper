from datetime import datetime

from termcolor import colored

from classes.IMessage import IMessage
from classes.IUser import IUser
import utils.request_handler


class IThread:
    __current_cursor: str | None = None
    __oldest_cursor: str | None = None
    __messages: list[IMessage] = []

    def __init__(self, id: int, title: str, is_group: bool, members: list[IUser] | None = None, oldest_cursor: str | None = None, current_cursor: str | None = None):
        self.id: int = id
        self.title: str = title
        self.is_group: bool = is_group

        self.members: list[IUser] = members
        self.__oldest_cursor = oldest_cursor
        self.__current_cursor = current_cursor

    def print(self):
        return f"{self.title} [{self.id}]"

    def fetch_messages(self, *, verbose: bool = False, limit_date: datetime | None = None, handler=None, refetch: bool = False) -> list[IMessage]:
        if handler is None:
            handler = utils.request_handler

        if len(self.__messages) > 0 and not refetch:
            return self.__messages

        while True:
            if verbose:
                print(colored(f"[*] Fetching messages for cursor {self.__current_cursor}", "blue"))

            response: dict = handler.get_request(f"/threads/{self.id}?cursor={self.__current_cursor if self.__current_cursor is not None else ""}", verbose=verbose)
            messages: list[dict] = response["thread"]["items"]

            # For every fetched message, create the proper object
            for message in messages:
                # First, ensure the message is after the limit date if it exists
                if (limit_date is None) or (datetime.fromtimestamp(int(message["timestamp"]) / 1000000) > limit_date):  # Again, Instagram uses MICROSECONDS for timestamps
                    self.__messages.append(IMessage.from_json(message))
                else:
                    break  # Limit date was reached. Break out of loop and return messages

            if response["thread"]["prev_cursor"] == "MINCURSOR" or response["thread"]["prev_cursor"] == self.__oldest_cursor:
                break

            self.__current_cursor = response["thread"]["prev_cursor"]

        return self.__messages

    @classmethod
    def from_id(cls, thread_id: int, *, handler=None):
        if handler is None:
            handler = utils.request_handler

        try:
            response: dict = handler.get_request(f"/threads/{thread_id}")
            thread_data = response["thread"]
        except Exception:
            return None

        # Create list of members
        members: list[IUser] = []
        for user in thread_data["users"]:
            members.append(IUser(user["id"], user["username"], user["full_name"], user["short_name"]))

        # Return the thread object
        # return cls(int(thread_data["thread_id"]), thread_data["thread_title"], thread_data["is_group"] == "true", members, thread_data["oldest_cursor"], thread_data["newest_cursor"])
        return cls(int(thread_data["thread_id"]), thread_data["thread_title"], thread_data["is_group"] == "true", members, thread_data["oldest_cursor"])


def fetch_threads(number: int = 200, *, handler=None) -> list[IThread]:
    if handler is None:
        handler = utils.request_handler

    response: dict = handler.get_request(f"/inbox/?persistentBadging=true&folder=&thread_message_limit=1&limit={number}")
    response_threads: list[dict] = response["inbox"]["threads"]  # Get the threads from the response

    to_return: list[IThread] = []

    # For every thread in the response list create the IThread object
    for response_thread in response_threads:
        to_return.append(IThread(int(response_thread["thread_id"]), response_thread["thread_title"], response_thread["is_group"] == "true"))

    return to_return
