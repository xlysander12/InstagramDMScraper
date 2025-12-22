Instagram DM Scraper (Real-Time Edition)
Description
This script allows you to archive entire Instagram DM histories into a searchable text file. This updated version is optimized for high-volume chats, featuring a live progress dashboard and critical stability fixes for large-scale data fetching.

##Key Improvements in this Version
KeyError Protection: Fixed a critical crash caused by media_share items (deleted or expired shared posts) that previously stopped fetches in long-running chats.

Live UI Dashboard: Added a real-time terminal display showing total messages fetched, total API requests, and elapsed time.

Stress Tested: Successfully verified with a continuous 18-hour run capturing 426,549 messages in a single session. (18 hours)

Windows Encoding Fix: Forced UTF-8 support to prevent emoji-related crashes on Windows terminals.

Dependency
This project uses pip for standard installation or uv as the package manager.

Standard Install:

pip install -r requirements.txt
Using uv:

Code snippet

pip install uv
uv init
uv sync

##How to start
Prerequisites: Ensure you have Python 3.x installed.

SessionID: You need the sessionid cookie from your browser.

Open Instagram in your browser and log in.

Open Developer Tools (F12) -> Storage (or Application) -> Cookies.

Copy the value of the sessionid cookie.

##Run the Script:

python main.py
Follow the Prompts: Enter your SessionID, select the chat from the list, and choose your filename (default: backup.txt).

Features
Inbox Explorer: See a numbered list of all your recent DMs.

High-Volume Fetching: Capable of handling hundreds of thousands of messages without memory leaks.

Live Status: Real-time feedback showing if the script is RUNNING or STALLED.

Auto-Save: Gracefully saves all captured data to your text file if interrupted (Ctrl+C).

##What's the sessionid?
The sessionid is a unique token Instagram uses to keep you logged in. 

## Force exit
If you need to stop the fetch before it reaches the beginning of the chat, simply press `Ctrl + C`. 
- The script will catch the interrupt signal.
- It will automatically begin processing and saving all messages fetched up to that moment.
- This ensures no data is lost even if you stop a massive run early.