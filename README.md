# Adrian's TikTok-Bot
## What is it?
A Discord bot that replies to TikTok links with the corresponding video file for that link.

Dependencies: Node.js, Selenium Webdriver, Axios, discord.js, discord-reply

## How does it work?
Uses Selenium WebDriver's headless browser to extract data from the given link.
Makes a get request with Axios on the URL of the video (found in the src tag of the HTML), streams the response to a file, and sends the file in chat on Discord.
Additionally interfaces with Heroku to host the bot 24/7 on the cloud.

## Required Permissions
- Read Messages/View Channels
- Send Messages
- Attach Files
- Read Message History
- Add Reactions
- Use Slash Commands