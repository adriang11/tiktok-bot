# Adrian's TikTok-Bot
## What is it?
A Discord bot that replies to TikTok links with the corresponding video file for that link.

Dependencies: Selenium Webdriver, Discord.py, Python's Requests library

## How does it work?
Uses Selenium WebDriver's headless browser to extract data from the given link.
Makes a get request with Axios on the URL of the video (found in the src tag of the HTML), streams the response to a file, and sends the file in chat on Discord.
Additionally interfaces with Heroku to host the bot 24/7 on the cloud.

## Required Permissions
- Read Messages/View Channels
- Send Messages
- Send Messages in Threads
- Attach Files
- Read Message History
- Add Reactions
- Use Slash Commands

## A Word About ChromeDriver
This bot uses Selenium that makes use of Chromedriver for Chrome to automate testing of websites.
When running this project locally, the installed version of Chromedriver should be in sync with the version of Chrome you are using.
You can find the latest stable builds  
https://googlechromelabs.github.io/chrome-for-testing/

## Challenges
Currently, the video is being loaded via JavaScript as a stream or Blob, and the actual media file isn't exposed via a direct HTTP link.
This goes against the original flow of the bot which scraped the video from the DOM of the webpage.
Working on a fix to go around this.