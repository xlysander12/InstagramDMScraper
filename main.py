import os
import sys
import threading
import time
import traceback
from datetime import datetime
# import curses

import requests
from termcolor import colored
import argparse

headers = {
	"accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
	'user-agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 105.0.0.11.118 (iPhone11,8; iOS 12_3_1; en_US; en-US; scale=2.00; 828x1792; 165586599)'
}

SESSIONID = None
THREADID = None
VERBOSE = False
FILE_PATH = None
PREV_CURSOR = "" # Internal Use
OLDEST_CURSOR = "" # Internal Use
USED_CURSORS: list = list() # Internal Use
LAST_RESPONSE = None
MESSAGES: list = list()
IS_WAITING = True
MEMBERS: dict = dict()
TOTAL_TIME = 0
RATE: list = [0]
LIMIT_DATE = None
REQUESTS_AMMOUNT = 0
STREAMED_MESSAGES: list = []
TO_STREAM: list = []
PARSER = argparse.ArgumentParser()
ARGS = None

# Creating args
PARSER.add_argument("-s" "--sessionid", dest="sessionid", type=str, help="Account's Sessionid")
PARSER.add_argument("-S", "--stream", dest="stream", action="store_true")
PARSER.add_argument("-t", "--threadid", dest="threadid", type=int, help="Chat's Threadid")
PARSER.add_argument("-v", "--verbose", dest="verbose", action="store_true")
PARSER.add_argument("-o", "--output", dest="output", type=str, help="Outfile file")
PARSER.add_argument("-d", "--date", dest="date", type=str, help="Limit date")
PARSER.add_argument("-l", "--list", dest="list", action="store_true")

def force_exit():
    """
    Called when the program is abruptely terminated (Like an exception or CTRL+C)
    """
    global IS_WAITING
    print(colored(f"Program exit before time... Printing fetched messages... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "red"))
    if IS_WAITING:
        IS_WAITING = False
    print_messages()


def rate_limit():
    global IS_WAITING
    IS_WAITING = False
    raise RuntimeError("You're being rate-limited")


def has_args():
    global ARGS
    return not (ARGS.date is None and ARGS.output is None and ARGS.sessionid is None and ARGS.stream is False and ARGS.threadid is None and ARGS.verbose is False)


def parse_args():
    global SESSIONID
    global THREADID
    global VERBOSE
    global FILE_PATH
    global LIMIT_DATE
    if ARGS.sessionid is None:
        return (False, "No Sessionid was provided")
    SESSIONID = ARGS.sessionid
    if ARGS.list:
        return (True, "list")
    if ARGS.threadid is None:
        return (False, "No Threadid was provided")
    THREADID = ARGS.threadid
    if ARGS.stream:
        return (True, "stream")

    VERBOSE = ARGS.verbose
    FILE_PATH = ARGS.output
    if ARGS.date is not None:
        if len(ARGS.date.split("@")) > 1:
            LIMIT_DATE = datetime.strptime(ARGS.date, "%d/%m/%Y@%H:%M:%S")
        else:
            LIMIT_DATE = datetime.strptime(ARGS.date, "%d/%m/%Y")
    return (True, None)


def get_request(url: str, headers: dict, cookies: dict):
    r = requests.get(url, headers=headers, cookies=cookies)
    global REQUESTS_AMMOUNT
    REQUESTS_AMMOUNT += 1
    if r.status_code != 200 and r.status_code == 429:
        rate_limit()
    try:
        res = r.json()
        global LAST_RESPONSE
        LAST_RESPONSE = res
        return res
    except json.JSONDecodeError:
        print(r.text)
        return None

def reverse_list(target_list):
    """
    Reverses the target list (Ex: [a, b, c] becomes [c, b, a])
    :param target_list:
    :return:
    """
    return [ele for ele in reversed(target_list)]

def get_messages(cursor: str = ""):
    """
    Request to get messages stored in that Cursor
    :param cursor:
    :return:
    """
    answer = get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{THREADID}/?cursor={cursor}", headers, {"sessionid": SESSIONID})["thread"]["items"]
    return answer

def has_prev_cursor(cursor):
    """
    Check if there's a Cursor older than the given one
    :param cursor:
    :return:
    """
    answer = bool(LAST_RESPONSE["thread"]["has_older"])
    return answer

def get_prev_cursor(cursor):
    """
    Get the most recent cursor older than the given one
    :param cursor:
    :return:
    """
    try:
        return LAST_RESPONSE["thread"]["prev_cursor"]
    except KeyError:
        try:
            return LAST_RESPONSE["thread"]["oldest_cursor"]
        except KeyError:
            return None

def get_all_messages(thread):
    """
    Main loop to get all messages playing around with Cursor and storing messages on the way
    :param thread:
    """
    global MESSAGES
    global RATE
    global TOTAL_TIME
    current_cursor = thread['newest_cursor']
    passed_limit_date = False
    while True:
        start = round(time.time()*1000)
        if current_cursor is None: break
        temp_messages = get_messages(current_cursor)
        to_add: list = list()
        Exists = False

        # Check if message is behind limit_date
        for temp_message in temp_messages:
            if VERBOSE:
                print(colored(f"[*] Checking message with id {temp_message['item_id']}", 'yellow'))
            if LIMIT_DATE is not None and LIMIT_DATE != "":
                msg_timestamp = datetime.fromtimestamp(temp_message["timestamp"] / 1000000)
                if LIMIT_DATE > msg_timestamp:
                    passed_limit_date = True
                    if VERBOSE:
                        print(colored(f"[-] Message timestamp is older than given limit. Canceling checks... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "red"))
                    break

            for mensagem in MESSAGES:
                if temp_message["item_id"] == mensagem["item_id"]:
                    Exists = True
                    if VERBOSE:
                        print(colored(f"[-] Repeated message... Moving on... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "red"))
                    break
            if Exists:
                continue
            to_add.append(temp_message)
            if VERBOSE:
                print(colored(f"[+] Message is valid. Moving to next message... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "green"))

        MESSAGES.extend(to_add)
        run_time = round(time.time() * 1000) - start
        try:
            rate = (1000*len(to_add)) / run_time
        except ZeroDivisionError:
            rate = RATE[len(RATE) - 1]
        RATE.append(rate)
        TOTAL_TIME += run_time


        if has_prev_cursor(current_cursor) and not passed_limit_date:
            current_cursor = get_prev_cursor(current_cursor)
        else:
            break


def start():
    """
    Where everything starts... duh
    """
    global MEMBERS
    global MESSAGES
    global TOTAL_TIME
    resposta = get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{THREADID}/?cursor=", headers, {"sessionid": SESSIONID})
    thread = resposta["thread"]
    for user in thread["users"]:
        MEMBERS[user["pk"]] = user["full_name"].split(" ")[0]
    MESSAGES = [thread["items"][0]]
    get_all_messages(thread)
    print_messages()

def start_streaming():
    global TO_STREAM
    global STREAMED_MESSAGES
    global MEMBERS
    # Get members list
    resposta = get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{THREADID}/?cursor=", headers, {"sessionid": SESSIONID})
    thread = resposta["thread"]
    for user in thread["users"]:
        MEMBERS[user["pk"]] = user["full_name"].split(" ")[0]

    # Get first Messages
    messages: dict = get_messages()
    for message in messages:
        TO_STREAM.append(message)
    print_messages(True)

    # Start loop that runs every 30 secs to fetch new messages
    while True:
        messages: dict = get_messages()
        for message in messages:
            if message["item_id"] not in STREAMED_MESSAGES:
                TO_STREAM.append(message)
        print_messages(True)
        time.sleep(10)

def get_threads():
    """
    Get a list of all chats the user from entered sessionid has
    """
    r = get_request("https://i.instagram.com/api/v1/direct_v2/inbox/?persistentBadging=true&folder=&thread_message_limit=1", headers, {"sessionid": SESSIONID})
    threads = r["inbox"]["threads"]
    threads_dict: dict = dict()
    for thread in threads:
        if thread["is_group"]:
            name: str = thread['thread_title']
        else:
            name: str = thread["users"][0]["full_name"]
        id = thread["thread_id"]
        threads_dict[id] = name
    for thread in threads_dict:
        print(f"{threads_dict.get(thread)} [{thread}]")


def print_messages(streaming: bool = False):
    """
    Function called to print and export all fetched messages
    """
    if not streaming:
        global IS_WAITING
        IS_WAITING = False
        print("----------- Messages -----------")
        for mensagem in reverse_list(MESSAGES):
            name = f"{MEMBERS[mensagem['user_id']]}: " if mensagem["user_id"] in MEMBERS else "You: "
            texto = ""
            if mensagem['item_type'] == 'text':
                texto = f"{mensagem['text']}"

            elif mensagem['item_type'] == 'media':
                if mensagem['media']['media_type'] == 1:
                    texto = f"Photo: {mensagem['media']['image_versions2']['candidates'][0]['url']}"
                elif mensagem['media']['media_type'] == 2:
                    texto = f"Video: {mensagem['media']['video_versions'][0]['url']}"

            elif mensagem['item_type'] == 'media_share':
                try:
                    texto = f"Post share from {mensagem['media_share']['user']['username']} (A.K.A {mensagem['media_share']['user']['full_name']}): https://instagram.com/p/{mensagem['media_share']['code']}/"
                except KeyError:
                    texto = f"Post share: Unable to get post"

            elif mensagem['item_type'] == 'voice_media':
                texto = f"Voice message: {mensagem['voice_media']['media']['audio']['audio_src']}"

            elif mensagem['item_type'] == 'raven_media':
                if mensagem['visual_media']['media']['media_type'] == 1:
                    try:
                        texto = f"Temporary photo: {mensagem['visual_media']['media']['image_versions2']['candidates'][0]['url']} (Might not work because might have expired already)"
                    except KeyError:
                        texto = f"Temporary photo: Unable to fetch (Probably expired already)"
                elif mensagem['visual_media']['media']['media_type'] == 2:
                    try:
                        texto = f"Temporary video: {mensagem['visual_media']['media']['video_versions'][0]['url']} (Might not work because might have expired already)"
                    except KeyError:
                        texto = f"Temporary video: Unable to fetch (Probably expired already)"
            else:
                texto = mensagem['item_type']
            timestamp_unix = float(mensagem["timestamp"]) / 1000000
            timestamp = datetime.fromtimestamp(timestamp_unix)
            if (VERBOSE and FILE_PATH is None) or (not VERBOSE and FILE_PATH is None) or VERBOSE:
                print(f"{colored(name, 'yellow')}{texto} [{timestamp.strftime('%d/%m/%Y @ %H:%M:%S')}]")
            if FILE_PATH is not None:
                with open(FILE_PATH, 'a+', encoding="UTF-8") as f:
                    f.write(f"{name}{texto} [{timestamp.strftime('%d/%m/%Y @ %H:%M:%S')}]\n")
                    f.close()
    else:
        global TO_STREAM
        global STREAMED_MESSAGES
        for mensagem in reverse_list(TO_STREAM):
            name = f"{MEMBERS[mensagem['user_id']]}: " if mensagem["user_id"] in MEMBERS else "Tu: "
            texto = ""
            if mensagem['item_type'] == 'text':
                texto = f"{mensagem['text']}"

            elif mensagem['item_type'] == 'media':
                if mensagem['media']['media_type'] == 1:
                    texto = f"Photo: {mensagem['media']['image_versions2']['candidates'][0]['url']}"
                elif mensagem['media']['media_type'] == 2:
                    texto = f"Video: {mensagem['media']['video_versions'][0]['url']}"

            elif mensagem['item_type'] == 'media_share':
                try:
                    texto = f"Post share from {mensagem['media_share']['user']['username']} (A.K.A {mensagem['media_share']['user']['full_name']}): https://instagram.com/p/{mensagem['media_share']['code']}/"
                except KeyError:
                    texto = f"Post share: Unable to get post"

            elif mensagem['item_type'] == 'voice_media':
                texto = f"Voice message: {mensagem['voice_media']['media']['audio']['audio_src']}"

            elif mensagem['item_type'] == 'raven_media':
                if mensagem['visual_media']['media']['media_type'] == 1:
                    try:
                        texto = f"Temporary photo: {mensagem['visual_media']['media']['image_versions2']['candidates'][0]['url']} (Might not work because might have expired already)"
                    except KeyError:
                        texto = f"Temporary photo: Unable to fetch (Probably expired already)"
                elif mensagem['visual_media']['media']['media_type'] == 2:
                    try:
                        texto = f"Temporary video: {mensagem['visual_media']['media']['video_versions'][0]['url']} (Might not work because might have expired already)"
                    except KeyError:
                        texto = f"Temporary video: Unable to fetch (Probably expired already)"
            else:
                texto = mensagem['item_type']
            timestamp_unix = float(mensagem["timestamp"]) / 1000000
            timestamp = datetime.fromtimestamp(timestamp_unix)
            print(f"{colored(name, 'yellow')}{texto} [{timestamp.strftime('%d/%m/%Y @ %H:%M:%S')}]")
            STREAMED_MESSAGES.append(mensagem["item_id"])
        TO_STREAM.clear()

def count_seconds():
    """
    I know this is a retarded way to do this, but its how I made it at the time and it works soooo, idc
    :return:
    """
    global TOTAL_TIME
    while IS_WAITING:
        time.sleep(1)
        TOTAL_TIME += 1

def waiting():
    """
    Thread to keep the "Fetching" text fancy
    """
    try:
        while IS_WAITING:
            if not VERBOSE:
                hours = int(((TOTAL_TIME / 1000) / (60 * 60)) % 24)
                minutes = int(((TOTAL_TIME / 1000) / 60) % 60)
                seconds = int((TOTAL_TIME / 1000) % 60)
                print(f"Fetching messages{'.' * ((int(TOTAL_TIME/1000) % 3) + 1)}{' ' * (4 - ((int(TOTAL_TIME/1000) % 3) + 1))}({f'{hours}h' if hours != 0 else ''}{f'{minutes}m' if hours != 0 or minutes != 0 else ''}{f'{seconds}s'}) ({len(MESSAGES)} fetched messages in {REQUESTS_AMMOUNT} requests) (Rate: {'{:.2f}'.format(RATE[len(RATE) - 1])} messages/second)", end="\r")
    except KeyboardInterrupt:
        pass

def compute_average_rate():
    return sum(RATE) / len(RATE)

def main():
    global THREADID
    global SESSIONID
    global ARGS
    global VERBOSE
    global LIMIT_DATE
    streaming = False
    ARGS = PARSER.parse_args()
    if has_args():
        success, message = parse_args()
        if not success:
            print(f"Error: {message}")
        else:
            if message is not None and message == "list":
                get_threads()
            elif message is not None and message == "stream":
                try:
                    streaming = True
                    start_streaming()
                except KeyboardInterrupt:
                    print(f"Streaming terminated!")
            else:
                if VERBOSE:
                    print("Fetching messages...")
                    print("----------- Verbose -----------")
                waiting_thread = threading.Thread(target=waiting)
                waiting_thread.daemon = True
                try:
                    waiting_thread.start()
                    start()
                except Exception as e:
                    traceback.print_exc()
                    force_exit()
    else:
        # signal.signal(signal.SIGINT, signal_handler)
        SESSIONID = input("Account's Sessionid: ")
        check_threads = input("See chats list (y/N): ")
        if check_threads == "y":
            get_threads()

        THREADID = input("Chat's Threadid: ")
        choice = input("(1) Dump chat log\n(2) Stream chat\n")
        if choice == "1":
            streaming = True
            enable_verbose = input("Verbose (y/N): ")
            if enable_verbose == "y":
                VERBOSE = True

            enable_export = input("Export to file (y/N): ")
            if enable_export == "y":
                FILE_PATH = input("File path + name: ")
                if os.path.isfile(FILE_PATH):
                    os.remove(FILE_PATH)

            temp_limit_date = input("Limite date (dd/mm/aa[@hh:mm:ss]): ")
            if temp_limit_date != "":
                if len(temp_limit_date.split("@")) > 1:
                    LIMIT_DATE = datetime.strptime(temp_limit_date, "%d/%m/%Y@%H:%M:%S")
                else:
                    LIMIT_DATE = datetime.strptime(temp_limit_date, "%d/%m/%Y")
            if VERBOSE:
                print("Fetching messages...")
                print("----------- Verbose -----------")
            waiting_thread = threading.Thread(target=waiting)
            waiting_thread.daemon = True
            try:
                waiting_thread.start()
                start()
            except Exception as e:
                traceback.print_exc()
                force_exit()

        else:
            try:
                start_streaming()
            except KeyboardInterrupt:
                print(f"Streaming terminated!")

    if not streaming:
        hours = int(((TOTAL_TIME/1000) / (60 * 60)) % 24)
        minutes = int(((TOTAL_TIME/1000) / 60) % 60)
        seconds = int((TOTAL_TIME/1000) % 60)
        if hours == 0 and minutes == 0:
            print(
                f"Fetching ended! A total of {len(MESSAGES)} messages were fetched in {seconds} {'seconds' if seconds != 1 else 'second'} with {REQUESTS_AMMOUNT} requests to the API and average of {'{:.2f}'.format(compute_average_rate())} messages/second")
        elif hours == 0 and minutes != 0:
            print(
                f"Fetching ended! A total of {len(MESSAGES)} messages were fetched in {minutes} {'minutes' if minutes != 1 else 'minute'}, {seconds} {'seconds' if seconds != 1 else 'second'} with {REQUESTS_AMMOUNT} requests to the API and average of {'{:.2f}'.format(compute_average_rate())} messages/second")
        else:
            print(
                f"Fetching ended! A total of {len(MESSAGES)} messages were fetched in {hours} {'hours' if hours != 1 else 'hour'}, {minutes} {'minutes' if minutes != 1 else 'minute'}, {seconds} {'seconds' if seconds != 1 else 'second'} with {REQUESTS_AMMOUNT} requests to the API and average of {'{:.2f}'.format(compute_average_rate())} messages/second")


if __name__ == '__main__':
    main()