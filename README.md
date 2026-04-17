### Instagram DM Scraper

## Description
Script to scrape Instagram DMs.
Supports both message dumping as well as live streaming of the chat.
Can be executed with no arguments, but also supports fully automated execution with arguments.

## Features
- See all DMs the user has
- Fetch all messages from any DM chat
- Fetch only messages more recent that specified date (optional)
- Export fetched messages to text file
- Stream the chat live. See the messages coming in in real time

## Requirements
- Python 3.13 or higher
- Download the source code (Either from releases or master branch)
- Install the required dependencies
  - Using pip: `pip install -r requirements.txt`
  - Using uv: `uv add -r requirements.txt` or just execute `uv sync`
- Next, you need the `sessionid` of the account you're trying to scrape from. See the section below.
- Once you have all that, just following the script's steps should get you where you need. You can also execute the main script with the `-h` or `--help` argument to learn more about executing with arguments.

## What's the sessionid?
The sessionid is a cookie that the Instagram website stores in your browser when there's an account logged in it.
If you need to find out the sessionid take a look at [CookiesGrabber](https://github.com/xlysander12/CookiesGrabber)
