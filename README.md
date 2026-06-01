# Adrian's TikTok-Bot
## What is it?
A Discord bot that replies to TikTok links with the corresponding video file for that link.

Dependencies: Selenium Webdriver, Discord.py, Python's Requests library

## How does it work?
Uses Selenium WebDriver's headless browser to extract the data needed to download videos or photo slideshows from a given TikTok link.
Once the media URL is found, the bot downloads the content directly from TikTok's CDN and uploads it back to Discord. If the file is too large for Discord's upload limits, it automatically sends a direct download link instead.
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

## 2025 Rework
The original version of the bot located the video URL directly from the rendered page and downloaded it from the DOM.
TikTok later changed how media is delivered, making the old approach unreliable. Rather than relying on visible page elements, the bot now extracts metadata from TikTok's embedded page data.
The bot loads the page with Selenium, parses the embedded JSON payload, retrieves the video's CDN URL, and downloads the media directly using the active browser session cookies.
This approach is more resilient to frontend UI changes and works for both standard videos and photo slideshows.