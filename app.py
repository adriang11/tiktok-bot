import os
import discord
import shutil
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
from selenium.common.exceptions import StaleElementReferenceException
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
        self.lastlink = ""
    
    async def on_ready(self):
        await self.wait_until_ready()
        if  not self.synced:
            await self.tree.sync()
            self.synced = True

        await self.change_presence(activity=discord.Game(name="League of Legends"))
        dungeon = client.get_channel(1149980884523556915)
        degens = client.get_channel(752401958647890108)
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

        headers = {
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36', 
            'Accept-Language':'en-US,en;q=0.9', 
            'Accept-Encoding':'gzip, deflate, br',
            'Accept':'text/html,application/x-protobuf,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer':'https://www.tiktok.com/'
        }

        service = Service(executable_path=CHROME_DRIVER_PATH)

        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument(f"user-agent={headers}")

        try:
            # strip link from message if appicable
            link = message.content
            print(f'[DEBUG TRACE] message detected: {link}\n')

            if link == self.lastlink:
                print(f'[DEBUG TRACE] last link matched: {link}\n')
                await message.reply(file=discord.File('output.mp4'))
                return

            lst = link.split(' ')
            for word in lst:
                if '.tiktok.com/' in word:
                    link = word

            print(f'[DEBUG TRACE] extracted link: {link}\n')

            # initialize the Selenium WebDriver
            # driver = webdriver.Chrome(service=service, options=options)
            driver = webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed

            driver.get(link)

            time.sleep(3)

            # allow page load before continuing
            # element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
            element = driver.find_element(By.TAG_NAME, 'video')

            print('[DEBUG TRACE] element found\n')
            
            try:
                source = element.find_element(By.TAG_NAME, 'source')
                url = source.get_attribute('src')
                
            except (NoSuchElementException, StaleElementReferenceException):
                print('[DEBUG TRACE] stale element found in src')
                url = element.get_attribute('src')

            all_cookies = driver.get_cookies()
            cookies = {cookies['name']:cookies['value'] for cookies in all_cookies}

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
                    #os.remove('output.mp4')
                    os.remove('output1.mp4')
                else:
                    await message.reply(file=discord.File('output.mp4'))
                    print('[DEBUG TRACE] file sent\n')
                    self.lastlink = link
                    #os.remove('output.mp4')
            else:
                print(r.status_code, '\n')
                await message.reply(content=('Status Code Error: ' + str(r.status_code) + ' (its over, we lost)'), mention_author=True)

            # time.sleep(30)

        except OSError as e:
            print('[DEBUG TRACE] WindowsError caught: ', e, '\n')
            await message.reply('Bot is working on another thing. Count to 10 and try again.')
        except TimeoutException as e:
            print('[DEBUG TRACE] TimeoutException caught: ', e, '\n')
            await message.reply('[ERROR] TimeoutException caught (Basically Heroku sucks)')
        except NoSuchElementException as e:
            print('[DEBUG TRACE] NoSuchElement caught, Testing for slideshow: ', e, '\n')
            try:
                driver.get_screenshot_as_file("screenshot.png")
                await message.reply(file=discord.File('screenshot.png'))

                wrapper = WebDriverWait(driver, 10, 0.5, (StaleElementReferenceException)).until(EC.presence_of_element_located((By.CLASS_NAME, "swiper-wrapper")))
                
                driver.get_screenshot_as_file("screenshot.png")
                await message.reply(file=discord.File('screenshot.png'))
                
                divs = WebDriverWait(wrapper, 10, 0.5, (StaleElementReferenceException)).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'div')))
                # divs = wrapper.find_elements(By.TAG_NAME, 'div')
                
                files = []
                found = []
                fnum = 0
                for i in divs:
                    if i.get_attribute('data-swiper-slide-index') not in found:
                        found.append(i.get_attribute('data-swiper-slide-index'))
                        container = i.find_element(By.TAG_NAME, 'img')
                        url = container.get_attribute('src')
                        all_cookies = driver.get_cookies()
                        cookies = {cookies['name']:cookies['value'] for cookies in all_cookies}

                        r = requests.get(url, cookies=cookies, headers=headers, stream=True)
                        
                        if len(files) == 9:
                            await message.channel.send(files=files)
                            num = 1
                            for file in files:
                                os.remove(f'img{num}.png')
                                num+=1
                            files.clear()
                            print('[DEBUG TRACE] files cleared\n')
                            fnum = 0
                        
                        filename = f"img{fnum+1}.png"
                        with open(filename, 'wb') as out_file:
                            fnum+=1
                            shutil.copyfileobj(r.raw, out_file)
                            files.append(discord.File(filename))
                        del r

                await message.channel.send(files=files)
                num = 1
                for file in files:
                    os.remove(f'img{num}.png')
                    num+=1
                files.clear()
                print('[DEBUG TRACE] files cleared\n')
                fnum = 0
            
            except Exception as e:
                print('oopsies\n')
                traceback.print_exc()
                await message.reply(content=("idk bot broke lawlz. mature content maybe?"), mention_author=True)

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

@client.tree.command(name = "coinflip", description = "flips a coin") 
async def coinflip(interaction: discord.Interaction):
    flip = random.randint(0,1)
    if(flip == 0):
        await interaction.response.send_message("Heads!")
    else:
        await interaction.response.send_message("Tails!")
    

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
    
    
    emojis = ['1️⃣','2️⃣', '3️⃣','4️⃣', '5️⃣', '6️⃣','7️⃣','8️⃣','9️⃣','🔟']
    options = [choice1, choice2, choice3, choice4, choice5, choice6, choice7,choice8,choice9,choice10]
    clean = False
    x = -1

    while(not clean):
        if (options[x] is None):
            options.pop()
        else:
            clean = True

    correctsize = range(len(options))

    for i in correctsize:
        options[i] = f"{emojis[i]} {options[i]} \n"
    options = '\n'.join(options)

    embed = discord.Embed(title=message, description=options, color=0x13a6f0)

    embed.set_footer(text="Poll created by somebody in the server xd")
    
    await interaction.response.send_message(embed=embed)
    sent = await interaction.original_response()

    for i in correctsize:
        await sent.add_reaction(emojis[i])

client.run(TOKEN)


