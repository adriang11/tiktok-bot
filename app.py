import os
import discord
import time
import traceback
import random
import requests
from discord import app_commands
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import SessionNotCreatedException
from selenium.common.exceptions import TimeoutException
from typing import Optional

load_dotenv()
TOKEN = os.getenv('TOKEN')
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.synced = False
        self.tree = app_commands.CommandTree(self)
    
    async def on_ready(self):
        await self.wait_until_ready()
        if  not self.synced:
            await self.tree.sync()
            self.synced = True

        await self.change_presence(activity=discord.Game(name="League of Legends"))
        dungeon = client.get_channel(1149980884523556915)
        degens = client.get_channel(1045937547597053982)
        ducklings = client.get_channel(915088526129909842)
        # await dungeon.send('I am alive and capable of feeling.')
        # await degens.send('I am alive and capable of feeling.')
        # await ducklings.send('I am alive and capable of feeling.')
        print(f'{client.user} is Ready to go!!')

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        
        if '.tiktok.com/' not in message.content:
            return

        service = Service(executable_path=CHROME_DRIVER_PATH)

        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')

        try:
            # strip link from message if appicable
            link = message.content
            print(f'[DEBUG TRACE] message detected: {link}\n')

            lst = link.split(' ')
            for word in lst:
                if '.tiktok.com/' in word:
                    link = word

            print(f'[DEBUG TRACE] extracted link: {link}\n')

            # initialize the Selenium WebDriver
            driver = webdriver.Chrome(service=service, options=options)

            driver.get(link)

            # allow page load before continuing (better fix in progress)
            time.sleep(3)
            
            # wait = WebDriverWait(driver, 3)
            # element = wait.until(EC.element_to_be_clickable((By.TAG_NAME, 'video')))
            element = driver.find_element(By.TAG_NAME, 'video')
            print('[DEBUG TRACE] element found\n')
            
            url = element.get_attribute('src')
            # print('[DEBUG TRACE] src link: ', url, '\n')

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
            
            if os.path.exists('output.mp4'):
                os.remove('output.mp4')
                print('[DEBUG TRACE] file removed\n')

            if r.status_code == 200:
                with open('output.mp4', 'wb') as f:
                    f.write(r.content)
                print('[DEBUG TRACE] video downloaded\n')

                # file validation, checks video codecs with ffmpeg and converts to mp4 if bitstream is hvec
                # os.system("ffmpeg.exe -v error -i output.mp4 -f null - >error.log 2>&1")
                os.system("ffprobe -loglevel quiet -select_streams v -show_entries stream=codec_name -of default=nw=1:nk=1 output.mp4 > log.txt 2>&1")
                log_file = open("log.txt","r")
                log_file_content = log_file.read()
                print('[DEBUG TRACE] ffmpeg error log: ', log_file_content)

                if 'h264' not in log_file_content:
                    os.system('ffmpeg -hide_banner -loglevel error -i output.mp4 output1.mp4')
                    await message.reply(file=discord.File('output1.mp4'))
                    print('[DEBUG TRACE] file sent, crisis averted\n')
                    os.remove('output.mp4')
                    os.remove('output1.mp4')
                else:
                    await message.reply(file=discord.File('output.mp4'))
                    print('[DEBUG TRACE] file sent\n')
                    os.remove('output.mp4')
            else:
                print(r.status_code, '\n')
                await message.reply(content=('Status Code Error: ' + str(r.status_code) + ' (its over, we lost)'), mention_author=True)

            # time.sleep(30)
        except WindowsError as e:
            print('[DEBUG TRACE] WindowsError caught: ', e.strerror, '\n')
            await message.reply('The bot is currently feeling a little overstimulated rn. Please try again in a few minutes.')
        except TimeoutException as e:
            print('[DEBUG TRACE] NoSuchElement caught: ', e, '\n')
            await message.reply('The bot currently does not support tiktok slideshows. Cry about it tbh')
        except NoSuchElementException as e:
            print('[DEBUG TRACE] NoSuchElement caught: ', e, '\n')
            await message.reply('The bot currently does not support tiktok slideshows. Cry about it tbh')
        except SessionNotCreatedException as e:
            print('[DEBUG TRACE] SessionNotCreated caught: ', e, '\n')
            await message.reply('[ERROR] Session not created: please notify Adrian to update Chromedriver')
        except Exception as e:
            if e.__class__ is discord.errors.HTTPException:
                print('[DEBUG TRACE] HTTPException caught: ', e, '\n')
                await message.reply(content=('Error: File too large. Maybe stop sending 12 minute tiktoks?'), mention_author=True)
            else:
                print('oopsies\n')
                traceback.print_exc()
                await message.reply(content=('Error: Unknown Error Occured. Please ping Adrian'), mention_author=True)
        finally:
            driver.quit()

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)

@client.tree.command(name = "test", description = "Says 'yo'. Nothing else") 
async def test_command(interaction: discord.Interaction):
    await interaction.response.send_message("yo")

@client.tree.command(name = "wisdom", description = "Receive a random wisdom from Pascal the Sea Otter") 
async def daily_wisdom(interaction: discord.Interaction):
    fd = open("wisdom.txt", "r", encoding='utf-8')
    lines = fd.readlines()
    wisdom = random.choice(lines)
    fd.close()
    print("Wisdom sent: ", wisdom)
    await interaction.response.send_message(wisdom)

@client.tree.command(name = "mywisdom", description = "Receive a random wisdom from Adrian the Chango") 
async def daily_wisdom(interaction: discord.Interaction):
    fd = open("wisdom1.txt", "r", encoding='utf-8')
    lines = fd.readlines()
    wisdom = random.choice(lines)
    fd.close()
    print("Wisdom sent: ", wisdom)
    await interaction.response.send_message(wisdom)

@client.tree.command(name = "divswisdom", description = "Receive a random wisdom from Divanni the Gomez") 
async def daily_wisdom3(interaction: discord.Interaction):
    fd = open("wisdomdiv.txt", "r", encoding='utf-8')
    lines = fd.readlines()
    wisdom = random.choice(lines)
    fd.close()
    print("Wisdom sent: ", wisdom)
    await interaction.response.send_message(wisdom)

@client.tree.command(name = "poll", description = "Creates a poll") 
async def test_command(interaction: discord.Interaction, message: str, choice1: str, choice2: str, choice3: Optional[str], choice4: Optional[str], choice5: Optional[str], choice6: Optional[str], choice7: Optional[str], choice8: Optional[str], choice9: Optional[str], choice10: Optional[str]):
    
    
    emojis = ['1️⃣','2️⃣']
    options = [choice1, choice2]
    
    for i in range(len(options)):
        options[i] = f"{emojis[i]} {options[i]} \n"
    options = '\n'.join(options)

    embed = discord.Embed(title=message, description=options, color=0x13a6f0)

    embed.set_footer(text="Poll created by somebody in the server xd")
    
    await interaction.response.send_message(embed=embed)
    sent = await interaction.original_response()
    for emoji in emojis:
        await sent.add_reaction(emoji)

client.run(TOKEN)


