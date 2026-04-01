import sys
from argparse import ArgumentParser

from classes import IThread
import utils.request_handler

parser = ArgumentParser()

parser.add_argument("-s" "--sessionid", dest="sessionid", type=str, help="Account's Sessionid")
parser.add_argument("-S", "--stream", dest="stream", action="store_true")
parser.add_argument("-t", "--threadid", dest="threadid", type=int, help="Chat's Threadid")
parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
parser.add_argument("-o", "--output", dest="output", type=str, help="Outfile file path")
parser.add_argument("-d", "--date", dest="date", type=str, help="Only show messages AFTER this date. Can either be a ISO String or Unix Timestamp")
parser.add_argument("-l", "--list", dest="list", action="store_true", help="List all existing threads")


def step_by_step():
    pass


def main():
    # Parse the arguments
    args = parser.parse_args()

    # If arguments were passed, execute the program with the arguments
    if len(sys.argv) > 1:
        # First, check if the sessionid arg was passed, if not, return with an error saying it's necessary
        if args.sessionid is None:
            raise Exception("Error: Sessionid is required")

        # Since the sessionid was passed, set it to the request handler
        utils.request_handler.set_sessionid(args.sessionid)

        # Next, if the 'list' argument was passed or if no thread id was passed, show all the possible threads
        if args.list is True or args.threadid is None:
            threads = IThread.fetch_threads()
            for thread in threads:
                print(thread)

            return

        # Fetch the thread data from the id
        thread = IThread.IThread.from_id(int(args.threadid))
        if thread is None:
            raise Exception("Something went wrong. Make sure the provided thread ID is valid")


if __name__ == "__main__":
    main()
