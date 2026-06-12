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
from discord import Member
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
from bot.data.statics import acronym_list
from bot.data.statics import no_free_views
from bot.data.statics import headers
from bot.services.ig_handler import handle_ig_link
from bot.utils.driver import create_driver
from bot.utils.validation import validate_file
from toolz import get_in
from typing import Optional
from typing import Literal
import pyshorteners
from .config import *

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.synced = False
        self.tree = app_commands.CommandTree(self)
        self.lastlink = ""
        self.toggle = False
        self.debugmode = False
        self.screencap = False
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
        if attribute == 'screencap':
            if not self.screencap:
                self.screencap = True
            else:
                self.screencap = False
            return self.screencap

    async def log(self, content, ctx):
        print(content)
        
        if self.debugmode: 
            await ctx.channel.send(content)

    async def breakpoint(self, content, driver, message):
        if self.debugmode and self.screencap: 
            driver.get_screenshot_as_file("screenshot.png")
            await message.channel.send(f"{content}", file=discord.File('screenshot.png'))

    async def handle_large_upload(self, ctx, cdn_url, spoilerwarning=False):
        self.lastlink = "" # Do not store video if large file
        try:   
            headers = {
                "Authorization": f"Bearer {TINYURL_KEY}",
                "Content-Type": "application/json"
            }

            r = requests.post(
                "https://api.tinyurl.com/create",
                headers=headers,
                json={"url": cdn_url},
                timeout=10
            )
            
            r.raise_for_status()

            short = r.json()["data"]["tiny_url"]
            
            await self.log(f"[DEBUG TRACE] Shortener Response: {short}\n", ctx)

            final_url = short if short else cdn_url
        except Exception as e:
            await self.log(f"[DEBUG TRACE] URL shortening failed: {e}\n", ctx)
            final_url = cdn_url
        
        if spoilerwarning: final_url= f"||{final_url}||"

        if isinstance(ctx, discord.Message):
            await ctx.reply(final_url)
            await self.log(f"[DEBUG TRACE] file sent", ctx)
        elif isinstance(ctx, discord.Interaction):
            await ctx.followup.send(final_url)
            await self.log(f"[DEBUG TRACE] file sent", ctx)

    async def handle_error(self, e, ctx, *, link="", retry=0):
        async def send_response(content, *, mention_author=True, delete_after=30):
            # Handle both discord.Message and discord.Interaction
            if isinstance(ctx, discord.Message):
                if self.debugmode: return await ctx.reply(content, mention_author=mention_author) #dont delete error if debugging
                else: return await ctx.reply(content, mention_author=mention_author, delete_after=delete_after)
            elif isinstance(ctx, discord.Interaction):
                await ctx.followup.send(link) 
                if self.debugmode: return await ctx.followup.send(content, ephemeral=False) 
                else: return await ctx.followup.send(content, ephemeral=True) 

        if isinstance(e, OSError):
            if str(e).startswith('No connection adapters were found for'):
                await self.log(f'[DEBUG TRACE] Blob link detected: {e}\n', ctx)
                if isinstance(ctx, discord.Interaction):
                    return await ctx.followup.send('If at first you don\'t succeed, try and try again', ephemeral=True) 
            else:
                await self.log(f'[DEBUG TRACE] WindowsError caught: {e}\n', ctx)
                await send_response('Bot is working on another thing. Count to 10 and try again.')
        elif isinstance(e, InvalidArgumentException):
            await self.log(f'[DEBUG TRACE] InvalidArgumentException caught: {e.msg}\n', ctx)
            if 'x.com/' in link:
                fixuplink = link.replace('x.com', 'fixupx.com', 1)

                if isinstance(ctx, discord.Interaction):
                    return await ctx.followup.send(fixuplink, ephemeral=True)
            else:
                await send_response('Please send a valid tiktok link...')
        elif isinstance(e, TimeoutException):
            await self.log(f'[DEBUG TRACE] TimeoutException caught: {e}\n', ctx)
            await send_response('Failure.')
        elif isinstance(e, SessionNotCreatedException):
            await self.log(f'[DEBUG TRACE] SessionNotCreated caught: {e}\n', ctx)
            await send_response('[ERROR] Session not created: please notify Adrian to update Chromedriver')
        elif isinstance(e, StaleElementReferenceException):
            await self.log(f'[DEBUG TRACE] StaleElementReferenceException caught: {e}\n', ctx)
            await send_response('Stale like a moldy piece of bread...')
        elif isinstance(e, discord.errors.HTTPException):
            await self.log(f'[DEBUG TRACE] HTTPException caught: {e}\n', ctx)
            self.lastlink = "" # Do not store video if error

            if isinstance(ctx, discord.Message):
                return await ctx.reply('enough.', mention_author=True, delete_after=30)
            elif isinstance(ctx, discord.Interaction):
                await ctx.followup.send(link)
                return await ctx.followup.send(':P', ephemeral=True)
        elif isinstance(e, int):
            await self.log(f'[DEBUG TRACE] Status Code Error Caught: {e} (its over, they\'re onto us)\n', ctx)
            if e == 429:
                await send_response('Rate Limited (They\'re onto us) Please try again in a moment')
            else:
                await send_response('Status Code Error: ' + str(e) + ' Please ping Adrian')
        else:
            await self.log(f'[DEBUG TRACE] Unknown Error Caught: {e}\n', ctx)
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
        if isinstance(ctx, discord.Message):
            link = ctx.content
        elif isinstance(ctx, discord.Interaction):
            link = userinput
        
        await self.log(f'[DEBUG TRACE] message detected: {link}\n', ctx)

        if link == self.lastlink:
            await self.log(f'[DEBUG TRACE] last link matched: {link}\n', ctx)
            await self.generic_output(ctx, link=link, spoilerwarning=spoilerwarning)
            return
        
        # strip link from message if appicable
        lst = link.split(' ')
        for word in lst:
            if '.tiktok.com/' in word:
                if word.startswith("||") and word.endswith("||"): spoilerwarning = True #foolproofing
                link = word.strip('||')

        await self.log(f'[DEBUG TRACE] extracted link: {link}\n', ctx)
        
        driver.get(link)

        # Run Prechecks
        try:
            maturecontent = WebDriverWait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'p')))
            for words in maturecontent:
                if words.text == 'Log in to TikTok':
                    await self.log(f'[DEBUG TRACE] Mature content detected\n', ctx)
                    if isinstance(ctx, discord.Interaction): await ctx.followup.send(link)
                    await self.generic_message(ctx, "Mature Content Detected. Gotta go to the app for this one buddy", ephemeral=False)
                    return
        except:
            pass

        await self.log(f'[DEBUG TRACE] No mature content detected\n', ctx)

        await self.breakpoint("1 - After Pre-checks:", driver, ctx)

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
            
            await self.log(f'[DEBUG TRACE] View stealing protected\n', ctx)

        return link

    async def find_video(self, driver, ctx):
        try:
            await self.log('[DEBUG TRACE] Searching for video\n', ctx)
            
            await self.breakpoint("3 - Checking for Video:", driver, ctx)

            element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
        
            await self.log('[DEBUG TRACE] element found\n', ctx)

            await self.breakpoint("4 - Video element detected:", driver, ctx)
            
            s = driver.page_source
            soup = BeautifulSoup(s, "html.parser")
            script_tag = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
            if script_tag:
                data = json.loads(script_tag.string)
                await self.log('[DEBUG TRACE] script found\n', ctx)

                play_url = get_in(["__DEFAULT_SCOPE__", "webapp.video-detail", "itemInfo", "itemStruct", "video", "bitrateInfo", 0, "PlayAddr", "UrlList", 2], data)

                await self.log(f"[DEBUG TRACE] CDN URL: {play_url}\n", ctx)

                url = play_url

            return url
        
        except TimeoutException as e:
            await self.breakpoint("4 - No video detected:", driver, ctx)

            await self.log(f'[DEBUG TRACE] TimeoutException caught, Testing for slideshow: {e.msg}\n', ctx)

            photoscheck = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "swiper-wrapper")))

            if photoscheck:  
                await self.log('[DEBUG TRACE] Photos found\n', ctx)
                return

    async def web_scrape(self, driver, ctx, headers, spoilerwarning, *, userinput=None, override=False):
            await self.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', ctx)

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
                    await self.log('[DEBUG TRACE] file removed\n', ctx)

                if r.status_code == 200:
                    with open('output.mp4', 'wb') as f:
                        f.write(r.content)
                    await self.log('[DEBUG TRACE] video downloaded\n', ctx)

                    log_file_content = validate_file()
                    
                    await self.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}', ctx)
                    if log_file_content == "":  
                        await self.handle_large_upload(ctx, url, spoilerwarning=spoilerwarning)
                    else:
                        try:
                            await self.generic_output(ctx, link=link, spoilerwarning=spoilerwarning)
                            await self.log('[DEBUG TRACE] file sent\n', ctx)
                            self.lastlink = link
                        except discord.HTTPException as e:
                            if e.code == 40005:
                                await self.handle_large_upload(ctx, url, spoilerwarning=spoilerwarning)
                            else:
                                raise
                else:
                    await self.log(f'[DEBUG TRACE] Error downloading video. Status code: {r.status_code}\n', ctx)
                    await self.handle_error(r.status_code, ctx, link=link)
    
    async def process_slideshow(self, driver, ctx, headers, spoilerwarning, *, userinput=None):
                await self.log(f'[DEBUG TRACE] Jarvis, initiate TikTok Photos protocol\n', ctx)

                await self.breakpoint("5 - slideshow 1:", driver, ctx)

                wrapper = WebDriverWait(driver, 10, 0.5, (StaleElementReferenceException)).until(EC.presence_of_element_located((By.CLASS_NAME, "swiper-wrapper")))
                await self.log(f'[DEBUG TRACE] wrapper found\n', ctx)
                divs = WebDriverWait(wrapper, 10, 0.5, (StaleElementReferenceException)).until(lambda x: x.find_elements(By.TAG_NAME, 'div'))
                await self.log(f'[DEBUG TRACE] div found\n', ctx)
                
                await self.breakpoint("6 - slideshow 2:", driver, ctx)

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
                            await self.log('[DEBUG TRACE] files cleared\n', ctx)
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
                await self.log('[DEBUG TRACE] files cleared\n', ctx)
                fnum = 0
                if isinstance(ctx, discord.Interaction):
                    await ctx.followup.send('<' + userinput + '>')

    async def process_ig(self, driver, ctx, headers, spoilerwarning):
        await self.log(f'[DEBUG TRACE] Entered IG flow', ctx)
        await handle_ig_link(self, driver, ctx, headers, spoilerwarning)

    async def on_message(self, message):
        spoilerwarning = False

        if message.author.id == self.user.id:
            return
        
        if self.toggle:
            test = await self.acronym_check(message)
            if test: return

        if '.tiktok.com/' not in message.content and '.instagram.com/' not in message.content:
            return

        if message.content.startswith("||") and message.content.endswith("||"):
            spoilerwarning = True

        service = Service(executable_path=CHROME_DRIVER_PATH)

        driver = create_driver(headers)

        try:
            if '.tiktok.com/' in message.content and '/@' not in message.content:
                await self.web_scrape(driver, message, headers, spoilerwarning)
            if '.instagram.com/' in message.content:
                # experimental feature
                await self.process_ig(driver, message, headers, spoilerwarning)
        except Exception as e: 
            await self.log(f'[DEBUG TRACE] Standard error detected: {e}\n', message)
            await self.handle_error(e, message)
        finally:
            driver.quit()
