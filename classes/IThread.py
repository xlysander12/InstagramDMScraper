import collections.abc
import time
from datetime import datetime

from termcolor import colored

from classes.IMessage import IMessage
from classes.IUser import IUser
import utils.request_handler


class IThread:
    __current_cursor: str | None = None
    __oldest_cursor: str | None = None
    __messages: list[IMessage] = []

    __done_fetching: bool = False
    __fetch_start_time: datetime | None = None

    def __init__(self, id: int, title: str, is_group: bool, members: list[IUser] | None = None, oldest_cursor: str | None = None, current_cursor: str | None = None):
        self.id: int = id
        self.title: str = title
        self.is_group: bool = is_group

        self.members: list[IUser] = members
        self.__oldest_cursor = oldest_cursor
        self.__current_cursor = current_cursor

    @property
    def done_fetching(self):
        return self.__done_fetching

    @property
    def fetch_start_time(self):
        return self.__fetch_start_time

    @property
    def num_of_messages(self) -> int:
        return len(self.__messages)

    def print(self):
        return f"{self.title} [{self.id}]"

    def message_exists(self, other_message: IMessage) -> bool:
        for message in self.__messages:
            if message == other_message:
                return True

        return False

    def fetch_messages(self, *, verbose: bool = False, limit_date: datetime | None = None, handler=None, use_stored: bool = False, chunk_callback = None) -> list[IMessage]:
        if handler is None:
            handler = utils.request_handler

        if use_stored:
            # Sort the messages
            self.__messages.sort(key=lambda m: m.timestamp)
            return self.__messages

        self.__fetch_start_time = datetime.now()

        try:
            while True:
                if verbose:
                    print(colored(f"[*] Fetching messages for cursor {self.__current_cursor} (Currently fetched: {self.num_of_messages})", "blue"))

                response: dict = handler.get_request(f"/threads/{self.id}?cursor={self.__current_cursor if self.__current_cursor is not None else ''}", verbose=verbose)
                messages: list[dict] = response["thread"]["items"]
                
                chunk_messages = []
                limit_reached = False

                # For every fetched message, create the proper object
                for message in messages:
                    # First, ensure the message is after the limit date if it exists
                    if (limit_date is None) or (datetime.fromtimestamp(int(message["timestamp"]) / 1000000) > limit_date):  # Instagram uses MICROSECONDS for timestamps
                        # Create message object
                        message_object = IMessage.from_json(message)

                        # Ensure the message is not repeated
                        if self.message_exists(message_object):
                            if verbose:
                                print(colored(f"[-] Repeated message... Moving on... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "red"))
                            continue

                        self.__messages.append(message_object)
                        chunk_messages.append(message_object)
                        
                        if verbose:
                            print(colored(f"[+] Message is valid (Total Fetched: {self.num_of_messages}). Moving to next message... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "green"))

                    else:  # Limit date was reached. Break out of loop and return messages
                        if verbose:
                            print(colored(f"[-] Message timestamp is older than given limit. Canceling checks... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "red"))
                        limit_reached = True
                        break

                if chunk_callback and len(chunk_messages) > 0:
                    chunk_callback(chunk_messages)
                    
                if limit_reached:
                    break

                if response["thread"]["prev_cursor"] == "MINCURSOR" or response["thread"]["prev_cursor"] == self.__oldest_cursor:
                    break

                try:
                    self.__current_cursor = response["thread"]["prev_cursor"]
                except KeyError:
                    self.__current_cursor = self.__oldest_cursor
        except BaseException as e:
            self.__done_fetching = True
            raise e

        self.__done_fetching = True

        # Sort all messages by timestamp, from oldest to most recent
        self.__messages.sort(key=lambda m: m.timestamp)

        return self.__messages

    def stream_messages(self, interval, *, handler=None):
        if handler is None:
            handler = utils.request_handler

        # Get the first batch of messages
        response: dict = handler.get_request(f"/threads/{self.id}")
        messages = response["thread"]["items"]

        # Add each message to the thread's messages list
        for message in messages:
            message_object = IMessage.from_json(message)
            self.__messages.append(message_object)

        # Order the messages
        self.__messages.sort(key=lambda m: m.timestamp)

        # Yield initially fetched messages
        yield self.__messages

        # Infinite loop that fetches new messages every 'interval' seconds
        time.sleep(interval)  # Initial timeout
        while True:
            response: dict = handler.get_request(f"/threads/{self.id}")
            messages = response["thread"]["items"]

            # Remove any duplicates from the list and store the new ones seperately
            new_messages: list[IMessage] = []
            for message in messages:
                message_object = IMessage.from_json(message)

                if self.message_exists(message_object):
                    continue

                new_messages.append(message_object)

            # Sort all new messages
            new_messages.sort(key=lambda m: m.timestamp)

            # Yield all new messages and update the total messages in object
            yield new_messages
            self.__messages.extend(new_messages)

            # Wait for 'interval' seconds
            time.sleep(interval)

    def get_member_from_id(self, id: int):
        for member in self.members:
            if member.id == id:
                return member

        return None

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
            members.append(IUser(int(user["id"]), user["username"], user["full_name"], user["short_name"]))

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
