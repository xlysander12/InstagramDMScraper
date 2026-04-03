import os.path
import threading
import time
from datetime import datetime, timedelta
import sys
from argparse import ArgumentParser

from classes import IThread
from utils import request_handler, misc

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
    try:
        time.sleep(1)  # Wait for 1 second before starting
        while thread.is_fetching:
            time_difference: timedelta = datetime.now() - thread.fetch_start_time
            hours, minutes, seconds = misc.hours_minutes_seconds_from_timedelta(time_difference)

            elipsis_str: str = f"{"." * ((int(time_difference.total_seconds()) % 3) + 1)}{" " * (4 - ((int(time_difference.total_seconds()) % 3) + 1))}"
            elapsed_time_str: str = f"{f"{hours}h" if hours != 0 else ""}{f"{minutes}m" if minutes != 0 else ""}{f"{seconds}s"}"
            total_messages_str: str = f"{thread.num_of_messages} fetched messages in {request_handler.number_of_requests} requests"
            rate_str: str = f"Rate: {"{:.2f}".format(thread.num_of_messages / time_difference.total_seconds())} messages/second"

            print(f"Fetching messages {elipsis_str} ({elapsed_time_str}) ({total_messages_str}) ({rate_str})", end="\r")

            time.sleep(1)  # Wait 1 second before looping again
    except KeyboardInterrupt:
        return


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
    # Create thread used to display the progress, if verbose is disabled
    waiting_thread = None
    if not verbose:
        waiting_thread = threading.Thread(target=waiting_thread_function, args=(thread,))
        waiting_thread.daemon = True
        waiting_thread.start()

    messages = thread.fetch_messages(verbose=verbose, limit_date=limit_date)

    # Build the message dump
    dump = ""
    for message in messages:
        author = thread.get_member_from_id(message.sender_id)
        author_name: str = f"{author.short_name} ({author.username})" if author is not None else "You"

        dump += f"{author_name}: {message.print()} [{message.timestamp.strftime('%d/%m/%Y @ %H:%M:%S')}]\n"

    # If an output file was given, write to it, otherwise, output the dump to the terminal
    if output_file is not None:
        with open(output_file, "w") as f:
            f.write(dump)
    else:
        if waiting_thread is not None:
            while waiting_thread.is_alive():
                pass
            else:
                # Clear the first line of the output to ensure clean output
                print(" " * 80, end="\r")

        print(dump)

        # Output finished message
        delta: timedelta = datetime.now() - thread.fetch_start_time
        hours, minutes, seconds = misc.hours_minutes_seconds_from_timedelta(delta)

        elapsed_time_str: str = f"{f"{hours} hours" if hours != 0 else ""}{f"{minutes} minutes" if minutes != 0 else ""}{f"{seconds} seconds" if seconds != 0 else ""}"
        print(f"Fetching ended! A total of {thread.num_of_messages} messages were fetched in {elapsed_time_str} with {request_handler.number_of_requests} requests to the API and an average of {"{:.2f}".format(thread.num_of_messages / delta.total_seconds())} messages/second")


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
                export_path: str = input("Export file path: ")

                # Check if file already exists
                if os.path.exists(export_path):
                    # If it does, make sure user wants to overwrite it
                    overwrite: bool = input("File already exists. Overwrite? (y/N) ") == "y"

                    if overwrite:
                        os.remove(export_path)
                        break
                    else:
                        continue
            else:
                break

        # Ask for limit date
        limit_date_answer: str = input("Limit date (dd/mm/aa[@hh:mm:ss]) (leave empty for none): ")
        limit_date = None
        if limit_date_answer != "":
            if limit_date_answer.split("@") > 1:
                limit_date: datetime = datetime.strptime(limit_date_answer, "%d/%m/%Y@%H:%M:%S")
            else:
                limit_date: datetime = datetime.strptime(limit_date_answer, "%d/%m/%Y")

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
    thread = IThread.IThread.from_id(int(args.threadid))
    if thread is None:
        raise Exception("Something went wrong. Make sure the provided thread ID is valid")

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
