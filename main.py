import sys
import os
import traceback

import requests
from datetime import datetime
import time
import threading
from termcolor import colored


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
logging = False
file_path = None
prevCursor = ""
oldestCursor = ""
used_cursors: list = list()
mensagens: list = list()
isWaiting = True
nome_remetente = None
id_remetente = None
seconds = 0
limit_date = None

def force_exit():
    """
    Called when the program is abruptely terminated (Like an exception or CTRL+C)
    """
    global isWaiting
    isWaiting = False
    print(colored("Program exit before time... Printing fetched messages...", "red"))
    print_messages()


def reverse_list(target_list):
    """
    Reverses the target list (Ex: [a, b, c] becomes [c, b, a])
    :param target_list:
    :return:
    """
    return [ele for ele in reversed(target_list)]

def getMessages(cursor):
    """
    Request to get messages stored in that Cursor
    :param cursor:
    :return:
    """
    return requests.get(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor={cursor}", headers=headers, cookies={"sessionid": sessionid}).json()["thread"]["items"]

def hasPrevCursor(cursor):
    """
    Check if there's a Cursor older than the given one
    :param cursor:
    :return:
    """
    return bool(requests.get(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor={cursor}", headers=headers, cookies={"sessionid": sessionid}).json()["thread"]["has_older"])

def getPrevCursor(cursor):
    """
    Get the most recent cursor older than the given one
    :param cursor:
    :return:
    """
    try:
        r = requests.get(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor={cursor}", headers=headers, cookies={"sessionid": sessionid})
        json = r.json()
        return json["thread"]["prev_cursor"]
    except KeyError:
        r = requests.get(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor={cursor}", headers=headers, cookies={"sessionid": sessionid})
        json = r.json()
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
            if limit_date is not None and limit_date != "":
                msg_timestamp = datetime.fromtimestamp(temp_message["timestamp"] / 1000000)
                if limit_date > msg_timestamp:
                    passed_limit_date = True
                    break

            for mensagem in mensagens:
                if temp_message["item_id"] == mensagem["item_id"]:
                    Exists = True
                if logging:
                    print("Repeted message found.... Rolling over it...")
                    break
            if Exists:
                break
            to_add.append(temp_message)

        mensagens.extend(to_add)
        if hasPrevCursor(current_cursor) and not passed_limit_date:
            current_cursor = getPrevCursor(current_cursor)
        else:
            break


def start():
    """
    Where everything starts... duh
    """
    global id_remetente
    global nome_remetente
    global mensagens
    resposta = requests.get(f"https://i.instagram.com/api/v1/direct_v2/threads/{threadid}/?cursor=", headers=headers, cookies={"sessionid": sessionid})
    thread = (resposta.json())["thread"]
    id_remetente = thread["users"][0]["pk"]
    nome_remetente = (thread["users"][0]["full_name"]).split(" ")[0]
    mensagens = [thread["items"][0]]
    getAllMessages(thread)
    # mensagens: list = reverse_list(thread["items"])
    print_messages()
    # start2()

def getThreads():
    """
    Get a list of all chats the user from entered sessionid has (only dm's, groups are not yet supported)
    """
    r = requests.get("https://i.instagram.com/api/v1/direct_v2/inbox/?persistentBadging=true&folder=&thread_message_limit=1", headers=headers, cookies={"sessionid": sessionid})
    threads = r.json()["inbox"]["threads"]
    threads_dict: dict = dict()
    for thread in threads:
        if thread["is_group"]:
            continue
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
    if enable_logging: print("----------------------------")
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

def print_messages():
    """
    Function called to print and export all fetched messages
    """
    for mensagem in reverse_list(mensagens):
        name = f"{colored(nome_remetente, 'green')}: " if mensagem["user_id"] == id_remetente else colored("Tu: ", 'yellow')
        texto = f"{mensagem['text'] if mensagem['item_type'] == 'text' else mensagem['item_type']}"
        # print(mensagem["timestamp"])
        timestamp_unix = float(mensagem["timestamp"]) / 1000000
        timestamp = datetime.fromtimestamp(timestamp_unix)
        global isWaiting
        isWaiting = False
        os.system("cls" if os.name == "nt" else "clear")
        if logging and file_path is None or not logging and file_path is None:
            print(f"{name}{texto} [{timestamp.strftime('%d/%m/%Y @ %H:%M:%S')}]")
        if file_path is not None:
            with open(file_path, 'a+', encoding="UTF-8") as f:
                f.write(f"{name}{texto} [{timestamp.strftime('%d/%m/Y @ %H:%M:%S')}]\n")
                f.close()

def waiting():
    """
    Thread to keep the "Fetching" text fancy
    """
    global seconds
    i = 0
    while isWaiting:
        os.system("cls" if os.name == "nt" else "clear")
        seconds += 1
        print(f"Fetching messages{'.' * i}")
        if i < 3:
            i += 1
        else:
            i = 0
        time.sleep(1)

if __name__ == '__main__':
    # signal.signal(signal.SIGINT, signal_handler)
    sessionid = input("Account's Sessionid: ")
    check_threads = input("See chats list (y/N): ")
    if check_threads == "y":
        getThreads()

    threadid = input("Chat's Threadid: ")
    enable_logging = input("Logging (y/N): ")
    if enable_logging == "y": logging = True

    enable_export = input("Export to file (y/N): ")
    if enable_export == "y":
        file_path = input("File path + name: ")
        if os.path.isfile(file_path):
            os.remove(file_path)

    temp_limit_date = input("Limite date (dd/mm/aa [hh:mm:ss]): ")
    if temp_limit_date != "":
        if len(temp_limit_date.split(" ")) > 1:
            limit_date = datetime.strptime(temp_limit_date, "%d/%m/%Y %H:%M:%S")
        else:
            limit_date = datetime.strptime(temp_limit_date, "%d/%m/%Y")
    if logging:
        print("----------- Logs -----------")
    x = threading.Thread(target=waiting)
    x.start()
    try:
        start()
    except Exception as e:
        traceback.print_exc()
        force_exit()
        sys.exit(0)
    hours = int((seconds / (60*60)) % 24)
    minutes = int((seconds / 60) % 60)
    seconds2 = int(seconds % 60)
    if hours == 0 and minutes == 0:
        print(f"All messages fetched! A total of {len(mensagens)} messages were fetched in {seconds2} {'seconds' if seconds2 != 1 else 'second'}")
    elif hours == 0 and minutes != 0:
        print(f"All messages fetched! A total of {len(mensagens)} messages were fetched in {minutes} {'minutes' if minutes != 1 else 'minute'}, {seconds2} {'seconds' if seconds2 != 1 else 'second'}")
    else:
        print(f"All messages fetched! A total of {len(mensagens)} messages were fetched in {hours} {'hours' if hours != 1 else 'hour'}, {minutes} {'minutes' if minutes != 1 else 'minute'}, {seconds2} {'seconds' if seconds2 != 1 else 'second'}")

    # start2()