import os
import base64
import discord
import gdshortener
import json
import shutil
import tempfile
import time
import traceback
import random
import requests
from bs4 import BeautifulSoup
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
from selenium.common.exceptions import InvalidArgumentException
from selenium.common.exceptions import SessionNotCreatedException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from statics import acronym_list
from statics import friends
from statics import headers
from toolz import get_in
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
        if isinstance(message, discord.Interaction):
            return
        
        if self.debugmode: 
            driver.get_screenshot_as_file("screenshot.png")
            await message.reply(f"{content}", file=discord.File('screenshot.png'))

    async def handle_large_upload(self, ctx, cdn_url):
        s = gdshortener.ISGDShortener()
        short = s.shorten(cdn_url)

        if isinstance(ctx, discord.Message):
            await ctx.reply(short[0])
        elif isinstance(ctx, discord.Interaction):
            await ctx.followup.send(short[0])

    async def handle_error(self, e, ctx, *, link="", retry=0):
        async def send_response(content, *, mention_author=True, delete_after=30):
            # Handle both discord.Message and discord.Interaction
            if isinstance(ctx, discord.Message):
                return await ctx.reply(content, mention_author=mention_author, delete_after=delete_after)
            elif isinstance(ctx, discord.Interaction):
                await ctx.followup.send(link) 
                return await ctx.followup.send(content, ephemeral=True) 

        if isinstance(e, OSError):
            if str(e).startswith('No connection adapters were found for'):
                print('[DEBUG TRACE] Blob link detected: ', e, '\n')
                if retry < 5:
                    return retry
                else:
                    if isinstance(ctx, discord.Interaction):
                        return await ctx.followup.send('If at first you don\'t succeed, try and try again', ephemeral=True) 
            else:
                print('[DEBUG TRACE] WindowsError caught: ', e, '\n')
                await send_response('Bot is working on another thing. Count to 10 and try again.')
        elif isinstance(e, InvalidArgumentException):
            print('[DEBUG TRACE] InvalidArgumentException caught: ', e.msg, '\n')
            await send_response('Please send a valid tiktok link...')
        elif isinstance(e, TimeoutException):
            print('[DEBUG TRACE] TimeoutException caught: ', e, '\n')
            await send_response('Failure.')
        elif isinstance(e, SessionNotCreatedException):
            print('[DEBUG TRACE] SessionNotCreated caught: ', e, '\n')
            await send_response('[ERROR] Session not created: please notify Adrian to update Chromedriver')
        elif isinstance(e, StaleElementReferenceException):
            print('[DEBUG TRACE] StaleElementReferenceException caught: ', e, '\n')
            await send_response('Stale like a moldy piece of bread...')
        elif isinstance(e, discord.errors.HTTPException):
            print('[DEBUG TRACE] HTTPException caught: ', e, '\n')
            client.lastlink = "" # Do not store video if error

            if isinstance(ctx, discord.Message):
                return await ctx.reply('enough.', mention_author=True, delete_after=30)
            elif isinstance(ctx, discord.Interaction):
                await ctx.followup.send(link)
                return await ctx.followup.send('File exceeds the size limit allowed on Discord. But just for you, imma send the link anyway so you can watch it on the Discord embed :D Also tell sharia that his bot needs to NOT respond to links sent by another bot', ephemeral=True)
        else:
            print('oopsies\n')
            traceback.print_exc()
            feedback = 'Unknown Error:' + str(e)
            await send_response(feedback, mention_author=True)

    async def generic_message(self, ctx, content, *, ephemeral=False):
        if isinstance(ctx, discord.Message):
            await ctx.reply(content)
        elif isinstance(ctx, discord.Interaction):
            await ctx.followup.send(content, ephemeral=ephemeral)

    async def generic_output(self, ctx, *, link="", spoilerwarning=False):
        if isinstance(ctx, discord.Message):
            await ctx.reply(file=discord.File('output.mp4', spoiler=spoilerwarning))
        elif isinstance(ctx, discord.Interaction):
            await ctx.followup.send('<' + link + '>')
            await ctx.channel.send(file=discord.File('output.mp4', spoiler=spoilerwarning))


    async def run_prechecks(self, driver, ctx, spoilerwarning, *, userinput=None, override=False):
        # strip link from message if appicable
        if isinstance(ctx, discord.Message):
            link = ctx.content
        elif isinstance(ctx, discord.Interaction):
            link = userinput
        
        print(f'[DEBUG TRACE] message detected: {link}\n')

        if link == self.lastlink:
            print(f'[DEBUG TRACE] last link matched: {link}\n')
            await self.generic_output(ctx, link=link, spoilerwarning=spoilerwarning)
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
                    if isinstance(ctx, discord.Interaction): await ctx.followup.send(link)
                    await self.generic_message(ctx, "Mature Content Detected. Gotta go to the app for this one buddy", ephemeral=True)
                    return
        except:
            pass

        print(f'[DEBUG TRACE] No mature content detected\n')

        await self.breakpoint("1 - After Pre-checks:", driver, ctx)

        no_free_views = ['@11adrian19','@rn.vg','@mnymchns','@po0japanchal']

        if not override:
            user = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:url']")))
            url = user.get_attribute("content")
            lst = url.split('/')
            
            for word in lst:
                if word.startswith("@"):
                    username = word
            if username in no_free_views:
                if isinstance(ctx, discord.Message):
                    await ctx.reply("No free views")
                elif isinstance(ctx, discord.Interaction):
                    await ctx.followup.send(link)
                    await ctx.followup.send("No free views", ephemeral=True)
                return
            
            print(f'[DEBUG TRACE] View stealing protected\n')

        return link

    async def find_video(self, driver, ctx):
        try:
            print('[DEBUG TRACE] Searching for video\n')
            
            await self.breakpoint("3 - After Photos Check (No Slideshow Detected):", driver, ctx)

            element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
        
            print('[DEBUG TRACE] element found\n')

            await self.breakpoint("4 - Video element detected:", driver, ctx)
            
            s = driver.page_source
            soup = BeautifulSoup(s, "html.parser")
            script_tag = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
            if script_tag:
                data = json.loads(script_tag.string)
                print('[DEBUG TRACE] script found\n')

                play_url = get_in(["__DEFAULT_SCOPE__", "webapp.video-detail", "itemInfo", "itemStruct", "video", "bitrateInfo", 0, "PlayAddr", "UrlList", 2], data)

                print("[DEBUG TRACE] CDN URL:", play_url, "\n")

                url = play_url

            return url
        
        except TimeoutException as e:
            await self.breakpoint("5 - After video check:", driver, ctx)

            print('[DEBUG TRACE] TimeoutException caught, Testing for slideshow: ', e, '\n')

            photoscheck = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "swiper-wrapper")))

            if photoscheck:  
                print('[DEBUG TRACE] Photos found\n')
                return

    async def web_scrape(self, driver, ctx, headers, spoilerwarning, *, userinput=None, override=False):
            print(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n')

            link = await self.run_prechecks(driver, ctx, spoilerwarning, userinput=userinput, override=override)
            if link is None: return
        
            url = await self.find_video(driver, ctx)

            if url is None:
                await self.process_slideshow(driver, ctx, headers, spoilerwarning, userinput=link)
        
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

                    try:
                        await self.generic_output(ctx, link=link, spoilerwarning=spoilerwarning)
                        print('[DEBUG TRACE] file sent\n')
                        self.lastlink = link
                    except discord.HTTPException as e:
                        if e.code == 40005:
                            await self.handle_large_upload(ctx, url)
                        else:
                            raise
                else:
                    print(r.status_code, '\n')
                    content='Status Code Error: ' + str(r.status_code) + ' (its over, they\'re onto us)'
                    await self.generic_message(content, ephemeral=True)
    
    async def process_slideshow(self, driver, ctx, headers, spoilerwarning, *, userinput=None):
                print(f'[DEBUG TRACE] Jarvis, initiate TikTok Photos protocol\n')
                
                await self.breakpoint("6 - slideshow 1:", driver, ctx)

                wrapper = WebDriverWait(driver, 10, 0.5, (StaleElementReferenceException)).until(EC.presence_of_element_located((By.CLASS_NAME, "swiper-wrapper")))
                print(f'[DEBUG TRACE] wrapper found\n')
                divs = WebDriverWait(wrapper, 10, 0.5, (StaleElementReferenceException)).until(lambda x: x.find_elements(By.TAG_NAME, 'div'))
                print(f'[DEBUG TRACE] div found\n')
                
                await self.breakpoint("7 - slideshow 2:", driver, ctx)

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
                            await ctx.channel.send(files=files)
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

                await ctx.channel.send(files=files)
                num = 1
                for file in files:
                    os.remove(f'img{num}.png')
                    num+=1
                files.clear()
                print('[DEBUG TRACE] files cleared\n')
                fnum = 0
                if isinstance(ctx, discord.Interaction):
                    await ctx.followup.send('<' + userinput + '>')

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
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-gpu")
        options.add_argument('--no-sandbox')
        options.add_argument(f"user-agent={headers}")

        # initialize the Selenium WebDriver
        # driver = webdriver.Chrome(service=service, options=options)
        driver = webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed

        try:
            if '.tiktok.com/' in message.content and '/@' not in message.content:
                await self.web_scrape(driver, message, headers, spoilerwarning)
        except Exception as e: 
            print(f'[DEBUG TRACE] Standard error detected', '\n')
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

@client.tree.command(name = "blame", description = "Tells you exactly who to blame for anything") 
async def blame(interaction: discord.Interaction):
    friend = random.choice(friends)
    print("Blame game played: ", friend)
    await interaction.response.send_message("This is clearly " + friend.title() + "\'s fault")

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

@client.tree.command(name="test_birthday", description="Display all registered birthday(s) in the server")
async def test_birthday(interaction: discord.Interaction, user: discord.User = None):
    members = {"1":{"Name":"rachelle","Birthday":"1/3"},
               "2":{"Name":"ruth","Birthday":"1/18"},
               "3":{"Name":"nik","Birthday":"4/24"},
               "4":{"Name":"josh","Birthday":"7/18"},
               "5":{"Name":"jasper","Birthday":"7/19"},
               "6":{"Name":"adrian","Birthday":"11/19"},
               "7":{"Name":"hari","Birthday":"11/22"},
               "8":{"Name":"sadiya","Birthday":"11/22"},
               "9":{"Name":"Fermi","Birthday":"12/6"},
               "10":{"Name":"Neha","Birthday":"12/19"}
               }

    if user is None:
        date_format = "%m/%d"
        
        sorted_birthdays = members

        items = list(members.items())

        mid = len(items) // 2

        first_half = items[:mid]
        second_half = items[mid:]

        interleaved = []
        for a, b in zip(first_half, second_half):
            interleaved.extend([a, b])

        # If odd length, add the leftover from first_half
        if len(first_half) > len(second_half):
            interleaved.append(first_half[-1])

        # Rebuild dictionary in new order
        freaky_style = dict(interleaved)

        columns = 0
        newline=False

        embed = discord.Embed(title=f"Degen Birthdays - {len(sorted_birthdays)}", color=discord.Color.blue())
        for member_id, member_data in freaky_style.items():
            if newline: 
                embed.add_field(name='\t',value='\t')
                newline=False

            name = member_data["Name"]
            birthday = member_data["Birthday"]
            embed.add_field(name=name, value=birthday, inline=True)
            columns+=1

            if columns==2:
                columns=0
                newline=True

        await interaction.response.send_message(embed=embed)
        
    else:
        user_id = str(user.id)
        if user_id in members:
            birthday = members[user_id]["Birthday"]
            color = members[user_id]["Color"]
            pfp = user.display_avatar
            embed = discord.Embed(title=f"{user.display_name}'s Birthday", color=discord.Color.from_str(color))
            embed.description = f"{birthday}"
            embed.set_thumbnail(url=pfp)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("This user has not registered!", ephemeral=True)
            return


@client.tree.command(name = "sugma", description = "Send tiktok without description")
async def sugma(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
    await interaction.response.defer()
    
    spoilerwarning = spoilered == "true"

    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-gpu")
    options.add_argument('--no-sandbox')
    options.add_argument(f"user-agent={headers}")

    driver = webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed

    try:
        await client.web_scrape(driver, interaction, headers, spoilerwarning, userinput=link)
    except Exception as e:
        print(f'[DEBUG TRACE] Standard error detected', '\n')
        await client.handle_error(e, interaction, link=link)
    finally:
        driver.quit()

@client.tree.command(name = "override", description = "Send tiktok overriding no free views")
async def override(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
    if interaction.user.id != 474713843181027328:
        await interaction.response.send_message("You are not Adrian.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    spoilerwarning = spoilered == "true"

    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-gpu")
    options.add_argument('--no-sandbox')
    options.add_argument(f"user-agent={headers}")

    driver = webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed

    try:
        await client.web_scrape(driver, interaction, headers, spoilerwarning, userinput=link, override=True)
    except Exception as e:
        print(f'[DEBUG TRACE] Standard error detected', '\n')
        await client.handle_error(e, interaction, link=link)
    finally:
        driver.quit()

@client.tree.command(name = "withcaption", description = "Send tiktok with description")
async def with_caption(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
    await interaction.response.defer()
    
    spoilerwarning = spoilered == "true"

    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-gpu")
    options.add_argument('--no-sandbox')
    options.add_argument(f"user-agent={headers}")

    driver = webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed

    try:
        print(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n')
        
        print(f'[DEBUG TRACE] message detected: {link}\n')

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
                    await client.generic_message(interaction, "Mature Content Detected. Gotta go to the app for this one buddy", ephemeral=True)
                    return
        except:
            pass

        print(f'[DEBUG TRACE] No mature content detected\n')

        await client.breakpoint("1 - After Pre-checks:", driver, interaction)

        no_free_views = ['@11adrian19','@rn.vg','@mnymchns','@po0japanchal']

        user = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:url']")))
        url = user.get_attribute("content")
        lst = url.split('/')

        for word in lst:
            if word.startswith("@"):
                username = word
        if username in no_free_views:
            await interaction.followup.send(link)
            await interaction.followup.send("No free views", ephemeral=True)
            return
        
        print(f'[DEBUG TRACE] Found username\n')
        
        meta = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:description']")))
        desc = meta.get_attribute("content")
        
        print(f'[DEBUG TRACE] Found description\n')

        header=None

        try:
           header = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text
           header = '**' + header + '**'
           print(f'[DEBUG TRACE] Found header\n')
        except:
            pass

        fulldesc = username + ': ' + desc

        if link == client.lastlink:
            print(f'[DEBUG TRACE] last link matched: {link}\n')
            await client.generic_output(interaction, link=link, spoilerwarning=spoilerwarning)
            if header: await interaction.channel.send(header)
            await interaction.channel.send(fulldesc)
            return

        url = await client.find_video(driver, interaction)

        if url is None:
            await client.process_slideshow(driver, interaction, headers, spoilerwarning, userinput=link)
            if header: await interaction.channel.send(header)
            await interaction.channel.send(fulldesc)
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

                try:
                    await client.generic_output(interaction, link=link, spoilerwarning=spoilerwarning)
                    if header: await interaction.channel.send(header)
                    await interaction.channel.send(fulldesc)
                    print('[DEBUG TRACE] file sent\n')
                    client.lastlink = link
                except discord.HTTPException as e:
                    if e.code == 40005:
                        await client.handle_large_upload(interaction, url)
                        if header: await interaction.channel.send(header)
                        await interaction.channel.send(fulldesc)
                    else:
                        raise
            else:
                print(r.status_code, '\n')
                content='Status Code Error: ' + str(r.status_code) + ' (its over, they\'re onto us)'
                await client.generic_message(content, ephemeral=True)
    except Exception as e:
        await client.handle_error(e, interaction, link=link)
    finally:
        driver.quit()

client.run(TOKEN)


