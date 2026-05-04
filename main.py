import os.path
import threading
import time
import traceback
from datetime import datetime, timedelta
import sys
import io
from argparse import ArgumentParser

from termcolor import colored

from classes import IThread
from utils import request_handler, misc

# Fix potential UnicodeEncodeError when printing emojis to terminal on Windows
if sys.stdout is not None and isinstance(sys.stdout, io.TextIOWrapper):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

parser = ArgumentParser()

parser.add_argument("-s", "--sessionid", dest="sessionid", type=str, help="Account's Sessionid")
parser.add_argument("-t", "--threadid", dest="threadid", type=int, help="Chat's Threadid")
parser.add_argument("-l", "--list", dest="list", action="store_true", help="List all existing threads")

streaming_group = parser.add_argument_group("Streaming options")
streaming_group.add_argument("-S", "--stream", dest="stream", action="store_true", help="Stream the chat instead of dumping contents. Updates in real time")
streaming_group.add_argument("-i", "--interval", dest="interval", default=10, help="Number of seconds between each message check. Lower values may trigger rate limits. Default: 10")

dumping_group = parser.add_argument_group("Dump options")
dumping_group.add_argument("-v", "--verbose", dest="verbose", action="store_true")
dumping_group.add_argument("-o", "--output", dest="output", type=str, help="Outfile file path")
dumping_group.add_argument("-d", "--date", dest="date", type=str, help="Only show messages AFTER this date. Format: 'dd/mm/yyyy[@hh:MM:ss]'")


def waiting_thread_function(thread: IThread.IThread):
    last_size_str: int = 0
    while not thread.done_fetching:
        time_difference: timedelta = datetime.now() - (thread.fetch_start_time if thread.fetch_start_time is not None else datetime.now())
        hours, minutes, seconds = misc.hours_minutes_seconds_from_timedelta(time_difference)

        fetched_str: str = f"Fetched: {thread.num_of_messages}"
        requests_str: str = f"Requests: {request_handler.number_of_requests}"
        
        secs = time_difference.total_seconds()
        rate_str: str = f"Rate: {'{:.2f}'.format(thread.num_of_messages / secs if secs > 0 else 0)} messages/second"
        elapsed_time_str: str = f"Elapsed Time: {hours:02}:{minutes:02}:{seconds:02}"

        output: str = f"Status: RUNNING | " + " | ".join([fetched_str, requests_str, rate_str, elapsed_time_str])

        print((" " * last_size_str) + "\r" + output, end="\r", flush=True)
        last_size_str = len(output)

        time.sleep(0.5)  # Wait half a second before looping again


def stream_thread(thread: IThread.IThread, interval: int):
    try:
        print(f"Starting streaming of thread {thread.id} with interval of {interval} seconds. Press Ctrl+C to stop")
        for new_messages in thread.stream_messages(interval):
            for message in new_messages:
                author = thread.get_member_from_id(message.sender_id)
                author_name: str = f"{author.short_name} ({author.username})" if author is not None else "You"

                print(f"{author_name}: {message.print()} [{message.timestamp.strftime('%d/%m/%Y @ %H:%M:%S')}]")
    except KeyboardInterrupt:
        print(f"Streaming terminated! Fetched a total of {thread.num_of_messages} messages with {request_handler.number_of_requests} requests to the API")
        return


def dump_messages(thread: IThread.IThread, verbose: bool, limit_date: datetime | None, output_file: str | None):
    # Wipe the file initially if it exists and write a clean slate
    if output_file is not None:
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"Warning: File '{output_file}' already has contents. Overwriting it.")
        with open(output_file, "w", encoding="utf-8") as f:
            pass

    def format_messages(msgs: list) -> str:
        formatted = ""
        for msg in msgs:
            author = thread.get_member_from_id(msg.sender_id)
            author_name: str = f"{author.short_name} ({author.username})" if author is not None else "You"
            formatted += f"{author_name}: {msg.print()} [{msg.timestamp.strftime('%d/%m/%Y @ %H:%M:%S')}]\n"
        return formatted

    # Callback used to write messages in real-time as they arrive chunk-by-chunk
    def on_chunk(chunk):
        if output_file is not None:
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(format_messages(chunk))

    # Create thread used to display the progress, if verbose is disabled
    waiting_thread = None
    if not verbose:
        waiting_thread = threading.Thread(target=waiting_thread_function, args=(thread,), daemon=True)
        waiting_thread.start()

    try:
        messages = thread.fetch_messages(verbose=verbose, limit_date=limit_date, chunk_callback=on_chunk)
    except BaseException as e:
        if waiting_thread is not None:
            while waiting_thread.is_alive():
                pass
            else:
                # Clear the first line of the output to ensure clean output
                print(" " * 100, end="\r")

        if isinstance(e, KeyboardInterrupt):
            print("\nDumping interrupted by user!")
        else:
            print(f"\nAn error occurred while fetching messages:\n{traceback.format_exc()}")
            
        messages = thread.fetch_messages(use_stored=True)  # This will return the already fetched messages

    # Build the message dump to stdout if NO output file was given
    if output_file is None:
        dump = format_messages(messages)

        if waiting_thread is not None:
            while waiting_thread.is_alive():
                pass
            else:
                # Clear the first line of the output to ensure clean output
                print(" " * 80, end="\r")

        print(dump, end="")
    else:
        if waiting_thread is not None:
            while waiting_thread.is_alive():
                pass
            else:
                # Clear the first line of the output to ensure clean output
                print(" " * 80, end="\r")

    # Output finished message
    delta: timedelta = datetime.now() - (thread.fetch_start_time if thread.fetch_start_time is not None else datetime.now())
    hours, minutes, seconds = misc.hours_minutes_seconds_from_timedelta(delta)

    elapsed_time_str: str = f"{f'{hours} hours ' if hours != 0 else ''}{f'{minutes} minutes ' if minutes != 0 else ''}{f'{seconds} seconds' if seconds != 0 else ''}"
    total_secs = delta.total_seconds()
    rate = "{:.2f}".format(thread.num_of_messages / total_secs if total_secs > 0 else 0)
    print(f"Fetching ended! A total of {thread.num_of_messages} messages were fetched in {elapsed_time_str} with {request_handler.number_of_requests} requests to the API and an average of {rate} messages/second")


def step_by_step():
    # Get the sessionid and apply it to the handler
    sessionid = input("Account's SessionID: ")
    request_handler.set_sessionid(sessionid)

    # Ask user if they want to see available threads
    check_threads = input("See chats list (y/N): ")
    if check_threads.lower() == "y":
        existing_threads = IThread.fetch_threads()

        for thread in existing_threads:
            print(thread.print())

    # Get the thread id
    thread_id = input("Thread ID: ")
    thread = IThread.IThread.from_id(thread_id)
    if thread is None:  # Ensure thread exists
        raise Exception("Something went wrong. Make sure the provided thread ID is valid")

    # Get the action (dump or stream)
    action = int(input("(1) Dump chat log\n(2) Stream chat\n> "))
    if action == 1:  # Dump selected
        # Ask if verbose
        enable_verbose: bool = input("Verbose (y/N): ").lower() == "y"

        # Ask if export
        while True:
            enable_export: bool = input("Export to file (y/N): ").lower() == "y"
            export_path = None
            if enable_export:
                export_path = input("Export file path: ")

                # Check if file already exists
                if os.path.exists(export_path):
                    # If it does, make sure user wants to overwrite it
                    overwrite: bool = input("File already exists. Overwrite? (y/N) ").lower() == "y"

                    if overwrite:
                        # dump_messages handles file wiping properly now.
                        break
                    else:
                        continue
                else:
                    break
            else:
                break

        # Ask for limit date
        limit_date_answer: str = input("Limit date (dd/mm/yyyy[@hh:mm:ss]) (leave empty for none): ")
        limit_date = None
        if limit_date_answer != "":
            if len(limit_date_answer.split("@")) > 1:
                limit_date = datetime.strptime(limit_date_answer, "%d/%m/%Y@%H:%M:%S")
            else:
                limit_date = datetime.strptime(limit_date_answer, "%d/%m/%Y")

        dump_messages(thread, enable_verbose, limit_date, export_path)
    else:  # Stream selected
        interval_str: str = input("Interval (seconds between captures) (default 10): ")
        interval: int = int(interval_str if interval_str != "" else 10)

        stream_thread(thread, interval)


def exec_with_args():
    # Parse the arguments
    args = parser.parse_args()

    # First, check if the sessionid arg was passed, if not, return with an error saying it's necessary
    if args.sessionid is None:
        raise Exception("Error: Sessionid is required")

    # Since the sessionid was passed, set it to the request handler
    request_handler.set_sessionid(args.sessionid)

    # Next, if the 'list' argument was passed or if no thread id was passed, show all the possible threads
    if args.list is True or args.threadid is None:
        threads = IThread.fetch_threads()
        for thread in threads:
            print(thread.print())

        return

    # Fetch the thread data from the id
    if args.verbose:
        print(colored("[*] Trying to fetch the Thread's data", "blue"))

    thread = IThread.IThread.from_id(int(args.threadid))
    if thread is None:
        raise Exception("Something went wrong. Make sure the provided thread ID is valid")

    if args.verbose:
        print(colored("[+] Fetched Thread's data", "green"))

    # Check if the stream argument was passed, if so, start streaming the thread
    if args.stream:
        stream_thread(thread, args.interval)

    else:  # Otherwise, do a proper message dump
        dump_messages(thread, args.verbose, args.date, args.output)


def main():
    # If arguments were passed, execute the program with the arguments
    if len(sys.argv) > 1:
        exec_with_args()
    else:
        step_by_step()


if __name__ == "__main__":
    main()
