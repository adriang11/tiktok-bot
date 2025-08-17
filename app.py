import os
import base64
import discord
import shutil
import tempfile
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
from statics import acronym_list
from statics import headers
from typing import Optional
from typing import Literal

load_dotenv()
TOKEN = os.getenv('TOKEN')
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')
WISDOM = os.getenv('ENCODED_FILE')
DIVS_WISDOM = os.getenv('DIVS_ENCODED_FILE')

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.synced = False
        self.tree = app_commands.CommandTree(self)
        self.lastlink = ""
        self.toggle = False
        self.debugmode = False
        self.wisdoms = []
        self.divswisdoms = []
    
    async def on_ready(self):
        await self.wait_until_ready()
        if  not self.synced:
            await self.tree.sync()
            self.synced = True

        await self.change_presence(activity=discord.Game(name="League of Legends"))

        dungeon = self.get_channel(os.getenv('DUNGEON'))
        degens = self.get_channel(os.getenv('DEGENS'))
        ducklings = self.get_channel(os.getenv('DUCKLINGS'))
        # await dungeon.send('I am alive and capable of feeling.')
        # await degens.send('I am alive and capable of feeling.')
        # await ducklings.send('I am alive and capable of feeling.')

        # Decode Wisdom files
        if WISDOM:
            try:
                self.wisdoms = base64.b64decode(WISDOM).decode("utf-8").splitlines()
            except Exception as e:
                print("[DEBUG TRACE] Failed to decode wisdom file:", e)
                self.wisdoms = ["ERROR: wisdom file invalid"]
        else:
            print("No wisdom file found in environment")
            self.wisdoms = ["ERROR: wisdom file missing"]
        
        if DIVS_WISDOM:
            try:
                self.divswisdoms = base64.b64decode(DIVS_WISDOM).decode("utf-8").splitlines()
            except Exception as e:
                print("[DEBUG TRACE] Failed to decode divs wisdom file:", e)
                self.divswisdoms = ["ERROR: divs wisdom file invalid"]
        else:
            self.divswisdoms = ["ERROR: divs wisdom file missing"]

        print(f'{self.user} is Ready to go!!')
    
    async def acronym_check(self, message):
        for word in message.content.split():
            word = word.strip('?.[]()1234567890!@#$%^&*,').lower()
            if word in acronym_list:
                await message.reply(acronym_list[word])
                return True
        
        return False
    
    async def toggler(self, attribute):
        if attribute == 'acronym':
            if not self.toggle:
                self.toggle = True
            else:
                self.toggle = False
            return self.toggle
        if attribute == 'debug':
            if not self.debugmode:
                self.debugmode = True
            else:
                self.debugmode = False
            return self.debugmode

    async def breakpoint(self, content, driver, message):
        if self.debugmode: 
            driver.get_screenshot_as_file("screenshot.png")
            await message.reply(f"{content}", file=discord.File('screenshot.png'))

    async def handle_error(self, e, ctx):
        async def send_response(content, *, mention_author=True, delete_after=30):
            # Handle both discord.Message and discord.Interaction
            if isinstance(ctx, discord.Message):
                return await ctx.reply(content, mention_author=mention_author, delete_after=delete_after)
            elif isinstance(ctx, discord.Interaction):
                # If response not sent yet, defer
                if not ctx.response.is_done():
                    await ctx.response.defer()
                return await ctx.followup.send(content, ephemeral=True)

        if isinstance(e, OSError):
            if str(e).startswith('No connection adapters were found for'):
                print('[DEBUG TRACE] Blob link detected: ', e, '\n')
                #await send_response('uummm')
            elif str(e).startswith('Invalid URL '):
                print('[DEBUG TRACE] Invalid URL Error: ', e, '\n')
                await send_response('CODED INCORRECTLY')
            else:
                print('[DEBUG TRACE] WindowsError caught: ', e, '\n')
                await send_response('Bot is working on another thing. Count to 10 and try again.')
        elif isinstance(e, TimeoutException):
            print('[DEBUG TRACE] TimeoutException caught: ', e, '\n')
            await send_response('Failure.')
        elif isinstance(e, SessionNotCreatedException):
            print('[DEBUG TRACE] SessionNotCreated caught: ', e, '\n')
            await send_response('[ERROR] Session not created: please notify Adrian to update Chromedriver')
        elif isinstance(e, StaleElementReferenceException):
            print('[DEBUG TRACE] StaleElementReferenceException caught: ', e, '\n')
            await send_response('Stale like a moldy piece of bread...')
        else:
            if e.__class__ is discord.errors.HTTPException:
                print('[DEBUG TRACE] HTTPException caught: ', e, '\n')
                client.lastlink = ""
                await send_response('enough.', mention_author=True, delete_after=30)
            else:
                print('oopsies\n')
                traceback.print_exc()
                feedback = 'Unknown Error:' + str(e)
                await send_response(feedback, mention_author=True)
        
    async def run_prechecks(self, driver, message, spoilerwarning):
        # strip link from message if appicable
        link = message.content  
        print(f'[DEBUG TRACE] message detected: {link}\n')

        if link == self.lastlink:
            print(f'[DEBUG TRACE] last link matched: {link}\n')
            await message.reply(file=discord.File('output.mp4', spoiler=spoilerwarning))
            return

        lst = link.split(' ')
        for word in lst:
            if '.tiktok.com/' in word:
                if word.startswith("||") and word.endswith("||"): spoilerwarning = True #foolproofing
                link = word.strip('||')

        print(f'[DEBUG TRACE] extracted link: {link}\n')
        
        driver.get(link)

        # Run Prechecks
        try:
            maturecontent = WebDriverWait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'p')))
            for words in maturecontent:
                if words.text == 'Log in to TikTok':
                    print(f'[DEBUG TRACE] Mature content detected\n')
                    await message.reply("Mature Content Detected. Gotta go to the app for this one buddy")
                    return
        except:
            pass

        print(f'[DEBUG TRACE] No mature content detected\n')

        self.breakpoint("1 - After Pre-checks:", driver, message)

        user = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:url']")))
        url = user.get_attribute("content")
        lst = url.split('/')
        for word in lst:
            if word.startswith("@"):
                username = word
        if username == '@11adrian19':
            await message.reply("No free views")
            return
        
        print(f'[DEBUG TRACE] View stealing protected\n')

        return link

    async def find_video(self, driver, message):
        try:
            print('[DEBUG TRACE] Searching for video\n')
            
            self.breakpoint("3 - After Photos Check (No Slideshow Detected):", driver, message)

            element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
        
            print('[DEBUG TRACE] element found\n')

            self.breakpoint("4 - Video element detected:", driver, message)
            
            try:
                source = element.find_element(By.TAG_NAME, 'source') 
                url = source.get_attribute('src')
                
                # if(url.startswith('blob')): url = url[5:]
                
                print(f'[DEBUG TRACE] video source: {url}\n')
            except NoSuchElementException as e:
                # try old logic:
                url = element.get_attribute('src')
                print(f'[DEBUG TRACE] erm ACTUALLY, this is the video source: {url}\n')

            # except StaleElementReferenceException:
            #     print('[DEBUG TRACE] Stale element found in src. Retrying...\n')
            #     driver.refresh()
            #     element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
            #     source = element.find_element(By.TAG_NAME, 'source')
            #     url = source.get_attribute('src')

            return url
        
        except TimeoutException as e:
            self.breakpoint("2 - After Metadata:", driver, message)

            print('[DEBUG TRACE] NoSuchElement caught, Testing for slideshow: ', e, '\n')

            photoscheck = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "swiper-wrapper")))

            if photoscheck:  
                print('[DEBUG TRACE] Photos found\n')
                return

    async def web_scrape(self, driver, message, headers, spoilerwarning):
            print(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n')

            # if isinstance(ctx, discord.Message):
            #     link = await self.run_prechecks(driver, ctx, spoilerwarning)
            #     if link is None: return
            # elif isinstance(ctx, discord.Interaction):
            #     link = userinput

            link = await self.run_prechecks(driver, message, spoilerwarning)
            if link is None: return

            url = await self.find_video(driver, message)

            if url is None:
                await self.process_slideshow(driver, message, headers, spoilerwarning)
            else:
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
                    os.system("ffprobe -loglevel quiet -select_streams v -show_entries stream=codec_name -of default=nw=1:nk=1 output.mp4 > log.txt 2>&1")
                    log_file = open("log.txt","r")
                    log_file_content = log_file.read()
                    print('[DEBUG TRACE] ffmpeg error log: ', log_file_content)

                    if 'h264' not in log_file_content:
                        print('[DEBUG TRACE] Hevc file detected. Checking for photos...\n')
                        await message.reply('Crisis averted... Thank me later', mention_author=True, delete_after=2)
                        await self.process_slideshow(driver, message, headers, spoilerwarning)
                    else:
                        await message.reply(file=discord.File('output.mp4', spoiler=spoilerwarning))
                        print('[DEBUG TRACE] file sent\n')
                        self.lastlink = link
                else:
                    print(r.status_code, '\n')
                    await message.reply(content=('Status Code Error: ' + str(r.status_code) + ' (its over, they\'re onto us)'), mention_author=True)

            
                # time.sleep(30)
    
    async def process_slideshow(self, driver, message, headers, spoilerwarning):
                print(f'[DEBUG TRACE] Jarvis, initiate TikTok Photos protocol\n')
                
                self.breakpoint("slideshow 1:", driver, message)

                wrapper = WebDriverWait(driver, 10, 0.5, (StaleElementReferenceException)).until(EC.presence_of_element_located((By.CLASS_NAME, "swiper-wrapper")))
                print(f'[DEBUG TRACE] wrapper found\n')
                divs = WebDriverWait(wrapper, 10, 0.5, (StaleElementReferenceException)).until(lambda x: x.find_elements(By.TAG_NAME, 'div'))
                print(f'[DEBUG TRACE] div found\n')
                
                self.breakpoint("slideshow 2:", driver, message)

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
                            files.append(discord.File(filename, spoiler=spoilerwarning))
                        del r

                await message.channel.send(files=files)
                num = 1
                for file in files:
                    os.remove(f'img{num}.png')
                    num+=1
                files.clear()
                print('[DEBUG TRACE] files cleared\n')
                fnum = 0

    async def on_message(self, message):
        spoilerwarning = False

        if message.author.id == self.user.id:
            return
        
        if self.toggle:
            test = await self.acronym_check(message)
            if test: return

        if '.tiktok.com/' not in message.content:
            return

        if message.content.startswith("||") and message.content.endswith("||"):
            spoilerwarning = True

        service = Service(executable_path=CHROME_DRIVER_PATH)

        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument(f"user-agent={headers}")

        # initialize the Selenium WebDriver
        # driver = webdriver.Chrome(service=service, options=options)
        driver = webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed

        try:
            if '.tiktok.com/' in message.content and '/@' not in message.content:
                await self.web_scrape(driver, message, headers, spoilerwarning)
   
        except NoSuchElementException as e:
            print('[DEBUG TRACE] NoSuchElement caught, Testing for slideshow: ', e, '\n')
            try:
                await self.process_slideshow(driver, message, headers, spoilerwarning)
            except TimeoutException as e:
                print('[DEBUG TRACE] Timeout Exception. Retrying...')
                await message.reply("Something went wrong. Retrying...", mention_author=True, delete_after=3)
                # retry logic:
                try:
                    await self.web_scrape(driver, message, headers, spoilerwarning)
                except:
                    await self.handle_error(e, message)
            except Exception as e:
                await self.handle_error(e, message)
        except Exception as e:
            await self.handle_error(e, message)
        finally:
            driver.quit()

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)

@client.tree.command(name = "test", description = "Says 'yo'. Nothing else") 
async def test_command(interaction: discord.Interaction):
    await interaction.response.send_message("yo")

@client.tree.command(name = "fortune", description = "Tells you a special fortune you need to hear") #using to determine version deployed on heroku
async def fortune(interaction: discord.Interaction):
    await interaction.response.send_message("Everyone is alive. Very few are living.")

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
async def adrians_wisdom(interaction: discord.Interaction):
    wisdom = random.choice(client.wisdoms)
    print("Wisdom sent: ", wisdom)
    await interaction.response.send_message(wisdom)

@client.tree.command(name = "divswisdom", description = "Receive a random wisdom from Divanni the Gomez") 
async def divs_wisdom3(interaction: discord.Interaction):
    wisdom = random.choice(client.divswisdoms)
    print("Wisdom sent: ", wisdom)
    await interaction.response.send_message(wisdom)

@client.tree.command(name = "toggle", description = "Toggle acronym troll on/off") 
async def toggle(interaction: discord.Interaction):
    tog = await client.toggler('acronym')
    response = "Acronym Help Mode set to " + str(tog)
    await interaction.response.send_message(response)

@client.tree.command(name = "debug", description = "Toggle debug mode on/off") 
async def debug(interaction: discord.Interaction):
    if interaction.user.id != 474713843181027328:
        await interaction.response.send_message("You are not Adrian.", ephemeral=True)
        return

    tog = await client.toggler('debug')
    response = "Debug Mode set to " + str(tog)
    await interaction.response.send_message(response)

@client.tree.command(name = "addwisdom", description = "Add wisdom like a boss") 
async def add_wisdom(interaction: discord.Interaction, message: str):
    if interaction.user.id != 474713843181027328:
        await interaction.response.send_message("You are not Adrian.", ephemeral=True)
        return
    
    with open("wisdomadrian.txt", 'a', encoding='utf-8') as file:
        file.write(message + '\n')
    
    await interaction.response.send_message(("Added new wisdom: " + message), ephemeral=True)

@client.tree.command(name = "poll", description = "Creates a poll") 
async def poll(interaction: discord.Interaction, message: str, choice1: str, choice2: str, choice3: Optional[str], choice4: Optional[str], choice5: Optional[str], choice6: Optional[str], choice7: Optional[str], choice8: Optional[str], choice9: Optional[str], choice10: Optional[str]):
    
    
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
    
    footer_text = 'Poll created by ' + interaction.user.display_name
    embed.set_footer(text=footer_text)
    
    await interaction.response.send_message(embed=embed)
    sent = await interaction.original_response()

    for i in correctsize:
        await sent.add_reaction(emojis[i])

@client.tree.command(name = "sugma", description = "Send tiktok without description")
async def sugma(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
    await interaction.response.defer()
    
    spoiler_warning = spoilered == "true"

    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument(f"user-agent={headers}")

    driver = webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed

    try:
        print(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n')
        
        if link == client.lastlink:
            print(f'[DEBUG TRACE] last link matched: {link}\n')
            await interaction.followup.send('<' + link + '>')
            await interaction.channel.send(file=discord.File('output.mp4', spoiler=spoiler_warning))
            return

        driver.get(link)

        try:
            maturecontent = WebDriverWait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'p')))
            for words in maturecontent:
                if words.text == 'Log in to TikTok':
                    print(f'[DEBUG TRACE] Mature content detected\n')
                    await interaction.followup.send("Mature Content Detected. Gotta go to the app for this one buddy", ephemeral=True)
                    return
        except:
            pass

        user = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:url']")))
        url = user.get_attribute("content")
        lst = url.split('/')
        username = None
        for word in lst:
            if word.startswith("@"):
                username = word
        if username == '@11adrian19':
            await interaction.followup.send('<' + link + '>')
            await interaction.followup.send("No free views")
            return

        print(f'[DEBUG TRACE] View stealing protected\n')

        try:
                photoscheck = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "swiper-wrapper")))

                if photoscheck:  
                    print('[DEBUG TRACE] photos found\n')
                    raise NoSuchElementException
                
        except TimeoutException:
            print('[DEBUG TRACE] Searching for video\n')
        
            # allow page load before continuing
            element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
            # element = driver.find_element(By.TAG_NAME, 'video')

            print('[DEBUG TRACE] element found\n')
            
            try:
                url = element.get_attribute('src')
                print(f'[DEBUG TRACE] video source: {url}\n')

                if url == '':
                    source = element.find_element(By.TAG_NAME, 'source') 
                    url = source.get_attribute('src')

                    print(f'[DEBUG TRACE] erm ACTUALLY, this is the video source: {url}\n')
                
            except StaleElementReferenceException:
                print('[DEBUG TRACE] Stale element found in src. Retrying...\n')
                driver.refresh()
                element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
                source = element.find_element(By.TAG_NAME, 'source')
                url = source.get_attribute('src')

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

            await interaction.followup.send('<' + link + '>')
            await interaction.channel.send(file=discord.File('output.mp4', spoiler=spoiler_warning))
            print('[DEBUG TRACE] file sent\n')
            client.lastlink = link

            # if 'h264' not in log_file_content:
            #     os.system('ffmpeg -hide_banner -loglevel error -i output.mp4 output1.mp4')
            #     await interaction.followup.send('<' + link + '>')
            #     await interaction.channel.send(file=discord.File('output1.mp4', spoiler=spoiler_warning))
            #     print('[DEBUG TRACE] file sent, crisis averted\n')
            #     await interaction.response.send_message(content=("uhhh lmk if it actually sent or if its that dumbass shaking tiktok logo i genuinely dont know"), ephemeral=True)
            #     os.remove('output1.mp4')
            # else:
            #     await interaction.followup.send('<' + link + '>')
            #     await interaction.channel.send(file=discord.File('output.mp4', spoiler=spoiler_warning))
            #     print('[DEBUG TRACE] file sent\n')
            #     client.lastlink = link
            #     #os.remove('output.mp4')
        else:
            print(r.status_code, '\n')
            await interaction.followup.send(content=('Status Code Error: ' + str(r.status_code) + ' (its over, they\'re onto us)'), ephemeral=True)

    
    except NoSuchElementException as e:
        print('[DEBUG TRACE] NoSuchElement caught, Testing for slideshow: ', e, '\n')
        try:
            print(f'[DEBUG TRACE] Jarvis, initiate TikTok Photos protocol\n')

            wrapper = WebDriverWait(driver, 10, 0.5, (StaleElementReferenceException)).until(EC.presence_of_element_located((By.CLASS_NAME, "swiper-wrapper")))
            divs = WebDriverWait(wrapper, 10, 0.5, (StaleElementReferenceException)).until(lambda x: x.find_elements(By.TAG_NAME, 'div'))

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
                        await interaction.channel.send(files=files)
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
                        files.append(discord.File(filename, spoiler=spoiler_warning))
                    del r

            await interaction.channel.send(files=files)
            num = 1
            for file in files:
                os.remove(f'img{num}.png')
                num+=1
            files.clear()
            print('[DEBUG TRACE] files cleared\n')
            fnum = 0
            await interaction.followup.send(content=('<' + link + '>'), ephemeral=True)
        except TimeoutException as e:
            await interaction.followup.send(content=("Failure."), ephemeral=True)
        except Exception as e:
            print('oopsies\n')
            traceback.print_exc()
            await interaction.followup.send(content=("idk bot broke lawlz. mature content maybe? xd"), ephemeral=True)
    
    except Exception as e:
        client.handle_error(e, interaction)
    finally:
        driver.quit()

@client.tree.command(name = "withcaption", description = "Send tiktok with description")
async def with_caption(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
    await interaction.response.defer()
    
    spoiler_warning = spoilered == "true"

    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument(f"user-agent={headers}")

    driver = webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed

    try:
        print(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n')

        driver.get(link)

        user = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:url']")))
        url = user.get_attribute("content")
        lst = url.split('/')
        for word in lst:
            if word.startswith("@"):
                username = word
        if username == '@11adrian19':
            await interaction.followup.send('<' + link + '>')
            await interaction.followup.send("No free views")
            return

        print(f'[DEBUG TRACE] Found username\n')

        meta = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:description']")))
        desc = meta.get_attribute("content")
        
        print(f'[DEBUG TRACE] Found description\n')

        fulldesc = username + ': ' + desc

        try:
                photoscheck = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "swiper-wrapper")))

                if photoscheck:  
                    print('[DEBUG TRACE] photos found\n')
                    raise NoSuchElementException
                
        except TimeoutException:
            print('[DEBUG TRACE] Searching for video\n')
        
            # allow page load before continuing
            element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
            # element = driver.find_element(By.TAG_NAME, 'video')

            print('[DEBUG TRACE] element found\n')
            
            try:
                source = element.find_element(By.TAG_NAME, 'source') 
                url = source.get_attribute('src')
                
            except (StaleElementReferenceException):
                print('[DEBUG TRACE] Stale element found in src. Retrying...\n')
                driver.refresh()
                element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
                source = element.find_element(By.TAG_NAME, 'source')
                url = source.get_attribute('src')

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
                await interaction.followup.send('<' + link + '>')
                await interaction.channel.send(file=discord.File('output1.mp4', spoiler=spoiler_warning))
                await interaction.channel.send(fulldesc)
                print('[DEBUG TRACE] file sent, crisis averted\n')
                await interaction.response.send_message(content=("uhhh lmk if it actually sent or if its that dumbass shaking tiktok logo i genuinely dont know"), ephemeral=True)
                os.remove('output1.mp4')
            else:
                await interaction.followup.send('<' + link + '>')
                await interaction.channel.send(file=discord.File('output.mp4', spoiler=spoiler_warning))
                await interaction.channel.send(fulldesc)
                print('[DEBUG TRACE] file sent\n')
                client.lastlink = link
                #os.remove('output.mp4')
        else:
            print(r.status_code, '\n')
            await interaction.followup.send(content=('Status Code Error: ' + str(r.status_code) + ' (its over, they\'re onto us)'), ephemeral=True)

    
    except NoSuchElementException as e:
        print('[DEBUG TRACE] NoSuchElement caught, Testing for slideshow: ', e, '\n')
        try:
            print(f'[DEBUG TRACE] Jarvis, initiate TikTok Photos protocol\n')

            wrapper = WebDriverWait(driver, 10, 0.5, (StaleElementReferenceException)).until(EC.presence_of_element_located((By.CLASS_NAME, "swiper-wrapper")))
            divs = WebDriverWait(wrapper, 10, 0.5, (StaleElementReferenceException)).until(lambda x: x.find_elements(By.TAG_NAME, 'div'))

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
                        await interaction.channel.send(files=files)
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
                        files.append(discord.File(filename, spoiler=spoiler_warning))
                    del r

            await interaction.channel.send(files=files)
            num = 1
            for file in files:
                os.remove(f'img{num}.png')
                num+=1
            files.clear()
            await interaction.channel.send(fulldesc)
            print('[DEBUG TRACE] files cleared\n')
            fnum = 0
            await interaction.followup.send(content=('<' + link + '>'), ephemeral=True)
        except TimeoutException as e:
            await interaction.followup.send(content=("Failure."), ephemeral=True)
        except Exception as e:
            print('oopsies\n')
            traceback.print_exc()
            await interaction.followup.send(content=("idk bot broke lawlz. mature content maybe? xd"), ephemeral=True)
    except OSError as e:
        if str(e).startswith('No connection adapters were found for'):
            print('[DEBUG TRACE] WindowsError caught: ', e, '\n')
            #await interaction.followup.send(content=('uummm'), ephemeral=True)
        else:
            print('[DEBUG TRACE] WindowsError caught: ', e, '\n')
            await interaction.followup.send(content=('Bot is working on another thing. Count to 10 and try again.'), ephemeral=True)
    except TimeoutException as e:
        print('[DEBUG TRACE] TimeoutException caught: ', e, '\n')
        await interaction.followup.send(content=('[ERROR] TimeoutException caught (Couldn\'t find video or slideshow'), ephemeral=True)
    except SessionNotCreatedException as e:
        print('[DEBUG TRACE] SessionNotCreated caught: ', e, '\n')
        await interaction.followup.send(content=('[ERROR] Session not created: please notify Adrian to update Chromedriver'), ephemeral=True)
    except Exception as e:
        if e.__class__ is discord.errors.HTTPException:
            print('[DEBUG TRACE] HTTPException caught: ', e, '\n')
            client.lastlink = ""
            await interaction.followup.send(content=('Error: File too large. Maybe stop sending 12 minute tiktoks?'), ephemeral=True)
        else:
            print('oopsies\n')
            traceback.print_exc()
            await interaction.followup.send(content=('Error: Unknown Error Occured.\nDon\'t even ping Adrian he\'ll see this... \n', e), ephemeral=True)
    finally:
        driver.quit()

client.run(TOKEN)


