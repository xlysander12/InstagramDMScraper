import time
import threading
import traceback
import os
from datetime import datetime
from termcolor import colored

# Global variables
MESSAGES = []
RATE = []
TOTAL_TIME = 0
VERBOSE = False
LIMIT_DATE = None
IS_WAITING = True
SESSIONID = None
THREADID = None
FILE_PATH = None
REQUESTS_AMMOUNT = 0
MEMBERS = {}
TO_STREAM = []
STREAMED_MESSAGES = []

def get_request(url, headers, params):
    # Function to perform the GET request (implementation needed)
    pass

def get_messages(current_cursor):
    # Function to get messages (implementation needed)
    pass

def reverse_list(lst):
    return lst[::-1]

def get_all_messages(thread):
    global MESSAGES
    global RATE
    global TOTAL_TIME
    current_cursor = thread['newest_cursor']
    passed_limit_date = False
    while True:
        start = round(time.time()*1000)
        if current_cursor is None:
            break
        temp_messages = get_messages(current_cursor)
        to_add: list = []
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
            rate = (1000 * len(to_add)) / run_time
        except ZeroDivisionError:
            rate = RATE[len(RATE) - 1]
        RATE.append(rate)
        TOTAL_TIME += run_time

        if has_prev_cursor(current_cursor) and not passed_limit_date:
            current_cursor = get_prev_cursor(current_cursor)
        else:
            break

def start():
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
    resposta = get_request(f"https://i.instagram.com/api/v1/direct_v2/threads/{THREADID}/?cursor=", headers, {"sessionid": SESSIONID})
    thread = resposta["thread"]
    for user in thread["users"]:
        MEMBERS[user["pk"]] = user["full_name"].split(" ")[0]
    
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
    r = get_request("https://i.instagram.com/api/v1/direct_v2/inbox/?persistentBadging=true&folder=&thread_message_limit=1&limit=200", headers, {"sessionid": SESSIONID})
    threads = r["inbox"]["threads"]
    threads_dict: dict = {}
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
                    # Check if the media is a post share
                    texto = f"Post share from {mensagem['media_share']['user']['username']} (A.K.A {mensagem['media_share']['user']['full_name']}): https://instagram.com/p/{mensagem['media_share']['code']}/"
                except KeyError:
                    texto = f"Post share: Unable to get post"

            elif mensagem['item_type'] == 'reel_media':  # Highlighted addition for reel media
                # Adding the logic to handle Instagram reels
                try:
                    texto = f"Reel share from {mensagem['reel_media']['user']['username']} (A.K.A {mensagem['reel_media']['user']['full_name']}): https://instagram.com/reel/{mensagem['reel_media']['code']}/"
                except KeyError:
                    texto = f"Reel share: Unable to get reel"

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

            elif mensagem['item_type'] == 'reel_media':  # Highlighted addition for reel media
                # Adding the logic to handle Instagram reels
                try:
                    texto = f"Reel share from {mensagem['reel_media']['user']['username']} (A.K.A {mensagem['reel_media']['user']['full_name']}): https://instagram.com/reel/{mensagem['reel_media']['code']}/"
                except KeyError:
                    texto = f"Reel share: Unable to get reel"

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

    if VERBOSE:
        print("Fetching ended! A total of {} messages were fetched in {} {} with {} requests to the API and average of {:.2f} messages/second".format(
            len(MESSAGES), minutes, 'minutes' if minutes != 1 else 'minute', REQUESTS_AMMOUNT, compute_average_rate()
        ))
    else:
        print("Fetching ended! A total of {} messages were fetched in {} {} with {} requests to the API and average of {:.2f} messages/second".format(
            len(MESSAGES), hours, 'hours' if hours != 1 else 'hour', REQUESTS_AMMOUNT, compute_average_rate()
        ))

if __name__ == '__main__':
    main()
