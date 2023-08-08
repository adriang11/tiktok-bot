import os
import discord
import time
import requests
from discord import app_commands
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


load_dotenv()
TOKEN = os.getenv('TOKEN')
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'{client.user} is Ready to go!!')
        # await tree.sync(guild=discord.Object(id=Your guild id))
        await self.change_presence(activity=discord.Game(name="League of Legends"))

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        
        if '.tiktok.com/' not in message.content:
            return

        service = Service(executable_path=CHROME_DRIVER_PATH)
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')

        try:
            # initialize the Selenium WebDriver
            driver = webdriver.Chrome(service=service, options=options)

            driver.get(message.content)
            print(f'tiktok link: {message.content}')
            element = driver.find_element(By.TAG_NAME, 'video')
            url = element.get_attribute('src')

            all_cookies = driver.get_cookies()
            cookies = {cookies['name']:cookies['value'] for cookies in all_cookies}

            headers = {
                'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36', 
                'Accept-Language':'en-US,en;q=0.9', 
                'Accept-Encoding':'gzip, deflate, br',
                'Accept':'text/html,application/x-protobuf,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Referer':'https://www.tiktok.com/'
                }

            r = requests.get(url, cookies=cookies, headers=headers)
            
            if r.status_code == 200:
                with open('output.mp4', 'wb') as f:
                    f.write(r.content)
                print('downloaded')
                await message.reply(file=discord.File('output.mp4'))
                os.remove('output.mp4')
            else:
                print(r.status_code, '\n')
                await message.reply(content=('Error: ' + r.status_code), mention_author=True)

            time.sleep(10)

        except Exception as e:
            print('oopsies\n', e)
            await message.reply(content=('Error: ' + str(e)), mention_author=True)
        finally:
            driver.quit()
    
    # @tree.command(name = "commandname", description = "My first application Command", guild=discord.Object(id=12417128931)) #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
    # async def first_command(interaction):
    #     await interaction.response.send_message("Hello!")

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
# tree = app_commands.CommandTree(client)

client.run(TOKEN)


