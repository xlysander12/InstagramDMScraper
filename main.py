import os
import threading
import time
import traceback
from datetime import datetime

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

sessionid = None
threadid = None
verbose = False
file_path = None
prevCursor = "" # Internal Use
oldestCursor = "" # Internal Use
used_cursors: list = list() # Internal Use
mensagens: list = list()
isWaiting = True
members: dict = dict()
seconds = 0
limit_date = None
requests_ammount = 0
streamed_messages: list = []
to_stream: list = []
parser = argparse.ArgumentParser()
args = None

# Creating args
parser.add_argument("-s" "--sessionid", dest="sessionid", type=str, help="Account's Sessionid")
parser.add_argument("-S", "--stream", dest="stream", action="store_true")
parser.add_argument("-t", "--threadid", dest="threadid", type=int, help="Chat's Threadid")
parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
parser.add_argument("-o", "--output", dest="output", type=str, help="Outfile file")
parser.add_argument("-d", "--date", dest="date", type=str, help="Limit date")
parser.add_argument("-l", "--list", dest="list", action="store_true")

def force_exit():
    """
    Called when the program is abruptely terminated (Like an exception or CTRL+C)
    """
    global isWaiting
    print(colored(f"Program exit before time... Printing fetched messages... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "red"))
    if isWaiting:
        isWaiting = False
        print_messages()


def rate_limit():
    global isWaiting
    isWaiting = False
    raise RuntimeError("You're being rate-limited")


def hasArgs():
    global args
    return not (args.date is None and args.output is None and args.sessionid is None and args.stream is False and args.threadid is None and args.verbose is False)


def parseArgs():
    global sessionid
    global threadid
    global verbose
    global file_path
    global limit_date
    if args.sessionid is None:
        return (False, "No Sessionid was provided")
    sessionid = args.sessionid
    if args.list:
        return (True, "list")
    if args.threadid is None:
        return (False, "No Threadid was provided")
    threadid = args.threadid
    if args.stream:
        return (True, "stream")

    verbose = args.verbose
    file_path = args.output
    if args.date is not None:
        if len(args.date.split("@")) > 1:
            limit_date = datetime.strptime(args.date, "%d/%m/%Y@%H:%M:%S")
        else:
            limit_date = datetime.strptime(args.date, "%d/%m/%Y")
    return (True, None)


def get_request(url: str, headers: dict, cookies: dict):
    r = requests.get(url, headers=headers, cookies=cookies)
    global requests_ammount
    requests_ammount += 1
    if r.status_code != 200 and r.status_code == 429:
        rate_limit()
    return r.json()

def reverse_list(target_list):
    """
    Reverses the target list (Ex: [a, b, c] becomes [c, b, a])
    :param target_list:
    :return:
    """
    return [ele for ele in reversed(target_list)]

def getMessages(cursor: str = ""):
    """
    Request to get messages stored in that Cursor
    :param cursor:
    :return:
    """
    answer = get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor={cursor}", headers, {"sessionid": sessionid})["thread"]["items"]
    return answer

def hasPrevCursor(cursor):
    """
    Check if there's a Cursor older than the given one
    :param cursor:
    :return:
    """
    answer = bool(get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor={cursor}", headers, {"sessionid": sessionid})["thread"]["has_older"])
    return answer

def getPrevCursor(cursor):
    """
    Get the most recent cursor older than the given one
    :param cursor:
    :return:
    """
    try:
        json = get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor={cursor}", headers, {"sessionid": sessionid})
        return json["thread"]["prev_cursor"]
    except KeyError:
        json = get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor={cursor}", headers, {"sessionid": sessionid})
        try:
            return json["thread"]["oldest_cursor"]
        except KeyError:
            return None

def getAllMessages(thread):
    """
    Main loop to get all messages playing around with Cursor and storing messages on the way
    :param thread:
    """
    global mensagens
    current_cursor = thread['newest_cursor']
    passed_limit_date = False
    while True:
        if current_cursor is None: break
        temp_messages = getMessages(current_cursor)
        to_add: list = list()
        Exists = False

        # Check if message is behind limit_date
        for temp_message in temp_messages:
            if verbose:
                print(colored(f"[*] Checking message with id {temp_message['item_id']}", 'yellow'))
            if limit_date is not None and limit_date != "":
                msg_timestamp = datetime.fromtimestamp(temp_message["timestamp"] / 1000000)
                if limit_date > msg_timestamp:
                    passed_limit_date = True
                    if verbose:
                        print(colored(f"[-] Message timestamp is older than given limit. Canceling checks... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "red"))
                    break

            for mensagem in mensagens:
                if temp_message["item_id"] == mensagem["item_id"]:
                    Exists = True
                    if verbose:
                        print(colored(f"[-] Repeated message... Moving on... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "red"))
                    break
            if Exists:
                break
            to_add.append(temp_message)
            if verbose:
                print(colored(f"[+] Message is valid. Moving to next message... [{datetime.now().strftime('%d/%m/%Y @ %H:%M:%S')}]", "green"))

        mensagens.extend(to_add)
        if hasPrevCursor(current_cursor) and not passed_limit_date:
            current_cursor = getPrevCursor(current_cursor)
        else:
            break


def start():
    """
    Where everything starts... duh
    """
    global members
    global mensagens
    resposta = get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor=", headers, {"sessionid": sessionid})
    thread = resposta["thread"]
    for user in thread["users"]:
        members[user["pk"]] = user["full_name"].split(" ")[0]
    mensagens = [thread["items"][0]]
    getAllMessages(thread)
    # mensagens: list = reverse_list(thread["items"])
    print_messages()
    # start2()

def start_streaming():
    global to_stream
    global streamed_messages
    global members
    # Get members list
    resposta = get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor=", headers, {"sessionid": sessionid})
    thread = resposta["thread"]
    for user in thread["users"]:
        members[user["pk"]] = user["full_name"].split(" ")[0]

    # Get first Messages
    messages: dict = getMessages()
    for message in messages:
        to_stream.append(message)
    print_messages(True)

    # Start loop that runs every 30 secs to fetch new messages
    while True:
        messages: dict = getMessages()
        for message in messages:
            if message["item_id"] not in streamed_messages:
                to_stream.append(message)
        print_messages(True)
        time.sleep(10)

def getThreads():
    """
    Get a list of all chats the user from entered sessionid has
    """
    r = get_request("https://i.instagram.com/api/v1/direct_v2/inbox/?persistentBadging=true&folder=&thread_message_limit=1", headers, {"sessionid": sessionid})
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

def start2():
    """
    Unused function that worked as a test during development but I'm afraid of removing so it stays here
    """
    global prevCursor
    global oldestCursor
    stopGettingMessages = False
    allMessages: list = []
    while prevCursor != "MINCURSOR" and not stopGettingMessages:
        getMessageAPIUrl = "https://i.instagram.com/api/v1/direct_v2/threads/" + threadid + "/"
        if oldestCursor is not None and len(oldestCursor) > 0:
            getMessageAPIUrl = getMessageAPIUrl + "?cursor=" + oldestCursor + ""

        r = requests.get(getMessageAPIUrl, headers=headers, cookies={"sessionid": sessionid})
        rjson = r.json()

        messages: list = rjson["thread"]["items"]
        for message in messages:
            isExists = False

            for i in range(len(allMessages)):
                existingElement = messages[i]
                if existingElement["item_id"] == message["item_id"]:
                    isExists = True
                    break

            if not isExists:
                allMessages.append(message)

            oldestCursor = rjson["thread"]["oldest_cursor"]
            prevCursor = rjson["thread"]["prev_cursor"]
    if enable_verbose: print("----------------------------")
    print_messages()

# def print_messages():
#     try:
#         while printing:
#             for mensagem in mensagens:
#                 name = f"{nome_remetente}: " if mensagem["user_id"] == id_remetente else "Tu: "
#                 texto = f"{mensagem['text'] if mensagem['item_type'] == 'text' else mensagem['item_type']}"
#                 print(f"{name}{texto}")
#             time.sleep(5000)
#     except NameError: time.sleep(5000)

def print_messages(streaming: bool = False):
    """
    Function called to print and export all fetched messages
    """
    if not streaming:
        global isWaiting
        isWaiting = False
        if not verbose:
            os.system("cls" if os.name == "nt" else "clear")
        else:
            print("----------- Messages -----------")
        for mensagem in reverse_list(mensagens):
            name = f"{members[mensagem['user_id']]}: " if mensagem["user_id"] in members else "Tu: "
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
            if (verbose and file_path is None) or (not verbose and file_path is None) or verbose:
                print(f"{colored(name, 'yellow')}{texto} [{timestamp.strftime('%d/%m/%Y @ %H:%M:%S')}]")
            if file_path is not None:
                with open(file_path, 'a+', encoding="UTF-8") as f:
                    f.write(f"{name}{texto} [{timestamp.strftime('%d/%m/%Y @ %H:%M:%S')}]\n")
                    f.close()
    else:
        global to_stream
        global streamed_messages
        for mensagem in reverse_list(to_stream):
            name = f"{members[mensagem['user_id']]}: " if mensagem["user_id"] in members else "Tu: "
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
            streamed_messages.append(mensagem["item_id"])
        to_stream.clear()

def waiting():
    """
    Thread to keep the "Fetching" text fancy
    """
    try:
        global seconds
        i = 0
        while isWaiting:
            seconds += 1
            if not verbose:
                os.system("cls" if os.name == "nt" else "clear")
                print(f"Fetching messages{'.' * i}{' ' * (4-i)}({seconds}s) ({len(mensagens)} fetched messages in {requests_ammount} requests)")
                if i < 3:
                    i += 1
                else:
                    i = 0
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    args = parser.parse_args()
    if hasArgs():
        success, message = parseArgs()
        if not success:
            print(f"Error: {message}")
        else:
            if message is not None and message == "list":
                getThreads()
            elif message is not None and message == "stream":
                try:
                    start_streaming()
                except KeyboardInterrupt:
                    print(f"Streaming terminated!")
            else:
                if verbose:
                    print("Fetching messages...")
                    print("----------- Verbose -----------")
                x = threading.Thread(target=waiting)
                x.start()
                try:
                    start()
                except Exception as e:
                    traceback.print_exc()
                    force_exit()
    else:
        # signal.signal(signal.SIGINT, signal_handler)
        sessionid = input("Account's Sessionid: ")
        check_threads = input("See chats list (y/N): ")
        if check_threads == "y":
            getThreads()

        threadid = input("Chat's Threadid: ")
        choice = input("(1) Dump chat log\n(2) Stream chat\n")
        if choice == "1":
            enable_verbose = input("Logging (y/N): ")
            if enable_verbose == "y": verbose = True

            enable_export = input("Export to file (y/N): ")
            if enable_export == "y":
                file_path = input("File path + name: ")
                if os.path.isfile(file_path):
                    os.remove(file_path)

            temp_limit_date = input("Limite date (dd/mm/aa[@hh:mm:ss]): ")
            if temp_limit_date != "":
                if len(temp_limit_date.split("@")) > 1:
                    limit_date = datetime.strptime(temp_limit_date, "%d/%m/%Y@%H:%M:%S")
                else:
                    limit_date = datetime.strptime(temp_limit_date, "%d/%m/%Y")
            if verbose:
                print("Fetching messages...")
                print("----------- Verbose -----------")
            x = threading.Thread(target=waiting)
            x.start()
            try:
                start()
            except Exception as e:
                traceback.print_exc()
                force_exit()
            hours = int((seconds / (60*60)) % 24)
            minutes = int((seconds / 60) % 60)
            seconds2 = int(seconds % 60)
            if hours == 0 and minutes == 0:
                print(f"Fetching ended! A total of {len(mensagens)} messages were fetched in {seconds2} {'seconds' if seconds2 != 1 else 'second'} with {requests_ammount} requests to the API")
            elif hours == 0 and minutes != 0:
                print(f"Fetching ended! A total of {len(mensagens)} messages were fetched in {minutes} {'minutes' if minutes != 1 else 'minute'}, {seconds2} {'seconds' if seconds2 != 1 else 'second'} with {requests_ammount} requests to the API")
            else:
                print(f"Fetching ended! A total of {len(mensagens)} messages were fetched in {hours} {'hours' if hours != 1 else 'hour'}, {minutes} {'minutes' if minutes != 1 else 'minute'}, {seconds2} {'seconds' if seconds2 != 1 else 'second'} with {requests_ammount} requests to the API")
        else:
            try:
                start_streaming()
            except KeyboardInterrupt:
                print(f"Streaming terminated!")

    # start2()