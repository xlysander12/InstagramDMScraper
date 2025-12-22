import os
import sys
import threading
import time
import json
from datetime import datetime
import requests
from termcolor import colored

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://www.instagram.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-ig-app-id": "936619743392459",
    "x-requested-with": "XMLHttpRequest",
}

SESSIONID = None
THREADID = None
FILE_PATH = None
LAST_RESPONSE = None
MESSAGES = []
IS_WAITING = True
MEMBERS = {}
REQUESTS_AMMOUNT = 0

def force_exit():
    global IS_WAITING
    print(colored(f"\n[!] Interrupt received. Attempting to save current progress...", "yellow"))
    IS_WAITING = False
    time.sleep(1)
    print_messages()
    sys.exit(0)

def get_request(url, cookies):
    global REQUESTS_AMMOUNT, LAST_RESPONSE
    try:
        r = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        REQUESTS_AMMOUNT += 1
        if r.status_code == 429:
            return "RATE_LIMIT"
        res = r.json()
        LAST_RESPONSE = res
        return res
    except: return None

def get_all_messages(thread):
    global MESSAGES
    current_cursor = thread.get('newest_cursor')
    while current_cursor:
        url = f"https://www.instagram.com/api/v1/direct_v2/threads/{THREADID}/?cursor={current_cursor}"
        res = get_request(url, {"sessionid": SESSIONID})
        
        if res == "RATE_LIMIT":
            time.sleep(30) 
            continue
            
        temp = res["thread"]["items"] if res and "thread" in res else []
        if not temp: break
        
        for msg in temp:
            if not any(m["item_id"] == msg["item_id"] for m in MESSAGES):
                MESSAGES.append(msg)
        
        if LAST_RESPONSE.get("thread", {}).get("has_older"):
            current_cursor = LAST_RESPONSE["thread"].get("prev_cursor") or LAST_RESPONSE["thread"].get("oldest_cursor")
            time.sleep(0.7) 
        else: break

def format_message(msg):
    t = msg.get('item_type', '')
    if t == 'text': return msg.get('text', '')
    if t == 'media': return "[Media Content]"
    
    if t == 'media_share': 
        share_data = msg.get('media_share')
        if share_data:
            code = share_data.get('code', '')
            return f"Shared Post: https://instagram.com/p/{code}/"
        return "[Shared Post - Unavailable/Deleted]"
        
    if t == 'voice_media': return "[Voice Message]"
    return f"[{t}]"

def print_messages():
    global IS_WAITING
    IS_WAITING = False
    if not MESSAGES:
        print(colored("No messages found to save.", "red"))
        return
    
    print(colored(f"\nProcessing {len(MESSAGES)} messages for output...", "cyan"))
    sorted_messages = sorted(MESSAGES, key=lambda x: x['timestamp'])
    
    output = []
    for m in sorted_messages:
        uid = m.get("user_id")
        name = f"{MEMBERS.get(uid, 'User')}: " if uid in MEMBERS else "You: "
        ts = datetime.fromtimestamp(float(m["timestamp"]) / 1000000).strftime('%d/%m/%Y @ %H:%M:%S')
        output.append(f"{name}{format_message(m)} [{ts}]")

    try:
        with open(FILE_PATH, 'w', encoding="utf-8") as f:
            f.write("\n".join(output) + "\n")
        print(colored(f"\nSUCCESS: Saved all messages to {FILE_PATH}", "green"))
    except Exception as e:
        print(colored(f"Error saving file: {e}", "red"))

def waiting():
    start_time = time.time()
    last_count = 0
    last_update = time.time()
    while IS_WAITING:
        cur = len(MESSAGES)
        status = colored("RUNNING", "green") if cur > last_count or (time.time() - last_update < 30) else colored("STALLED", "red")
        
        if cur > last_count:
            last_count, last_update = cur, time.time()
        
        elapsed_seconds = int(time.time() - start_time)
        h, rem = divmod(elapsed_seconds, 3600)
        m, s = divmod(rem, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
        
        print(f"\rStatus: [{status}] | Fetched: {cur} | Requests: {REQUESTS_AMMOUNT} | Time: {time_str} ", end="", flush=True)
        time.sleep(1)

def main():
    global THREADID, SESSIONID, FILE_PATH
    print(colored("=== Instagram DM Scraper (Real-Time Edition) ===\n", "cyan"))
    
    SESSIONID = input("Enter SessionID: ")
    
    print("Fetching recent chats...")
    list_url = "https://www.instagram.com/api/v1/direct_v2/inbox/?persistent_badging=true&folder=&thread_message_limit=1"
    inbox = get_request(list_url, {"sessionid": SESSIONID})
    
    if isinstance(inbox, dict) and "inbox" in inbox:
        print(f"\n{'Index':<6} | {'Thread ID':<25} | {'Users'}")
        print("-" * 75)
        threads = inbox["inbox"]["threads"]
        for i, thr in enumerate(threads):
            users = ", ".join([u["full_name"] for u in thr.get("users", [])])
            display_users = (users[:40] + '...') if len(users) > 40 else users
            print(f"{i:<6} | {thr['thread_id']:<25} | {display_users}")
        
        selection = input("\nEnter Index # or paste Thread ID: ")
        if selection.isdigit() and int(selection) < len(threads):
            THREADID = threads[int(selection)]["thread_id"]
        else:
            THREADID = selection
    else:
        THREADID = input(colored("\nCould not load inbox. Enter Thread ID manually: ", "yellow"))

    raw_path = input("Enter filename (default: backup.txt): ").strip()
    FILE_PATH = raw_path if raw_path else "backup.txt"
    
    t = threading.Thread(target=waiting, daemon=True)
    t.start()
    
    res = get_request(f"https://www.instagram.com/api/v1/direct_v2/threads/{THREADID}/", {"sessionid": SESSIONID})
    
    if res and res != "RATE_LIMIT":
        for u in res["thread"].get("users", []):
            MEMBERS[u["pk"]] = u["full_name"].split(" ")[0]
        get_all_messages(res["thread"])
        print_messages()
    else:
        print(colored("\nConnection failed. Your SessionID might be rate-limited.", "red"))

if __name__ == '__main__':
    try: 
        main()
    except KeyboardInterrupt: 
        force_exit()
    except Exception as e:
        print(colored(f"\nAn unexpected error occurred: {e}", "red"))
        force_exit()