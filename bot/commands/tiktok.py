import os
import discord
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bot.data.statics import headers
from toolz import get_in
from typing import Literal


def register(client):
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
            await client.log(f'[DEBUG TRACE] Standard error detected: {e}\n', interaction)
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
            await client.log(f'[DEBUG TRACE] Standard error detected: {e}\n', interaction)
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
            await client.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', interaction)
            
            await client.log(f'[DEBUG TRACE] message detected: {link}\n', interaction)

            lst = link.split(' ')
            for word in lst:
                if '.tiktok.com/' in word:
                    if word.startswith("||") and word.endswith("||"): spoilerwarning = True #foolproofing
                    link = word.strip('||')

            await client.log(f'[DEBUG TRACE] extracted link: {link}\n', interaction)
            
            driver.get(link)

            # Run Prechecks
            try:
                maturecontent = WebDriverWait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'p')))
                for words in maturecontent:
                    if words.text == 'Log in to TikTok':
                        await client.log(f'[DEBUG TRACE] Mature content detected\n', interaction)
                        await interaction.followup.send(link)
                        await client.generic_message(interaction, "Mature Content Detected. Gotta go to the app for this one buddy", ephemeral=True)
                        return
            except:
                pass

            await client.log(f'[DEBUG TRACE] No mature content detected\n', interaction)

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
            
            await client.log(f'[DEBUG TRACE] Found username\n', interaction)
            
            meta = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:description']")))
            desc = meta.get_attribute("content")
            
            await client.log(f'[DEBUG TRACE] Found description\n', interaction)

            if len(desc)>2000:
                desc = desc[:1900] + "..."
                await client.log(f'[DEBUG TRACE] Description shrunk\n', interaction)

            header=None

            try:
                header = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text
                header = '**' + header + '**'
                await client.log(f'[DEBUG TRACE] Found header\n', interaction)
            except:
                pass

            fulldesc = '*' + username + ':* ' + desc

            if link == client.lastlink:
                await client.log(f'[DEBUG TRACE] last link matched: {link}\n', interaction)
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
                    await client.log('[DEBUG TRACE] file removed\n', interaction)

                if r.status_code == 200:
                    with open('output.mp4', 'wb') as f:
                        f.write(r.content)
                    await client.log('[DEBUG TRACE] video downloaded\n', interaction)

                    # file validation, checks video codecs with ffmpeg and converts to mp4 if bitstream is hvec
                    os.system("ffprobe -loglevel quiet -select_streams v -show_entries stream=codec_name -of default=nw=1:nk=1 output.mp4 > log.txt 2>&1")
                    log_file = open("log.txt","r")
                    log_file_content = log_file.read()
                    await client.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}', interaction)

                    try:
                        await client.generic_output(interaction, link=link, spoilerwarning=spoilerwarning)
                        if header: await interaction.channel.send(header)
                        await interaction.channel.send(fulldesc)
                        await client.log('[DEBUG TRACE] file sent\n', interaction)
                        client.lastlink = link
                    except discord.HTTPException as e:
                        if e.code == 40005:
                            await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                            if header: await interaction.channel.send(header)
                            await interaction.channel.send(fulldesc)
                        else:
                            raise
                else:
                    await client.log(f'[DEBUG TRACE] Error downloading video: {r.status_code}\n', interaction)
                    await client.handle_error(r.status_code, interaction, link=link)
        except Exception as e:
            await client.handle_error(e, interaction, link=link)
        finally:
            driver.quit()

    @client.tree.command(name = "candice", description = "for dev testing: sends 3 CDN url links shortened")
    async def candice(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
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
            await client.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', interaction)
            
            await client.log(f'[DEBUG TRACE] message detected: {link}\n', interaction)

            lst = link.split(' ')
            for word in lst:
                if '.tiktok.com/' in word:
                    if word.startswith("||") and word.endswith("||"): spoilerwarning = True #foolproofing
                    link = word.strip('||')

            await client.log(f'[DEBUG TRACE] extracted link: {link}\n', interaction)
            
            driver.get(link)

            # Run Prechecks
            try:
                maturecontent = WebDriverWait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'p')))
                for words in maturecontent:
                    if words.text == 'Log in to TikTok':
                        await client.log(f'[DEBUG TRACE] Mature content detected\n', interaction)
                        await interaction.followup.send(link)
                        await client.generic_message(interaction, "Mature Content Detected. Gotta go to the app for this one buddy", ephemeral=True)
                        return
            except:
                pass

            await client.log(f'[DEBUG TRACE] No mature content detected\n', interaction)

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
            
            await client.log(f'[DEBUG TRACE] Found username\n', interaction)
            
            meta = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:description']")))
            desc = meta.get_attribute("content")
            
            await client.log(f'[DEBUG TRACE] Found description\n', interaction)

            if len(desc)>2000:
                desc = desc[:1900] + "..."
                await client.log(f'[DEBUG TRACE] Description shrunk\n', interaction)

            header=None

            try:
                header = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text
                header = '**' + header + '**'
                await client.log(f'[DEBUG TRACE] Found header\n', interaction)
            except:
                pass

            fulldesc = '*' + username + ':* ' + desc

            if link == client.lastlink:
                await client.log(f'[DEBUG TRACE] last link matched: {link}\n', interaction)
                await client.generic_output(interaction, link=link, spoilerwarning=spoilerwarning)
                if header: await interaction.channel.send(header)
                await interaction.channel.send(fulldesc)
                return

            try:
                await client.log('[DEBUG TRACE] Searching for video\n', interaction)
                
                await client.breakpoint("3 - After Photos Check (No Slideshow Detected):", driver, interaction)

                element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
            
                await client.log('[DEBUG TRACE] element found\n', interaction)

                await client.breakpoint("4 - Video element detected:", driver, interaction)
                
                s = driver.page_source
                soup = BeautifulSoup(s, "html.parser")
                script_tag = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
                if script_tag:
                    data = json.loads(script_tag.string)
                    await client.log('[DEBUG TRACE] script found\n', interaction)

                    play_url1 = get_in(["__DEFAULT_SCOPE__", "webapp.video-detail", "itemInfo", "itemStruct", "video", "bitrateInfo", 0, "PlayAddr", "UrlList", 2], data)
                    play_url2 = get_in(["__DEFAULT_SCOPE__", "webapp.video-detail", "itemInfo", "itemStruct", "video", "bitrateInfo", 0, "PlayAddr", "UrlList", 1], data)
                    play_url3 = get_in(["__DEFAULT_SCOPE__", "webapp.video-detail", "itemInfo", "itemStruct", "video", "bitrateInfo", 0, "PlayAddr", "UrlList", 0], data)

                    await client.log(f'[DEBUG TRACE] CDN URL1: {play_url1}\n', interaction)
                    await client.log(f'[DEBUG TRACE] CDN URL2: {play_url2}\n', interaction)
                    await client.log(f'[DEBUG TRACE] CDN URL3: {play_url3}\n', interaction)

                    url1 = play_url1
                    url2 = play_url2
                    url3 = play_url3
            
            except TimeoutException as e:
                await client.breakpoint("5 - After video check:", driver, interaction)

                await client.log(f'[DEBUG TRACE] TimeoutException caught, Testing for slideshow: {e}\n', interaction)

                photoscheck = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "swiper-wrapper")))

                if photoscheck:  
                    await client.log('[DEBUG TRACE] Photos found\n', interaction)
                    return

            for url in [url1,url2,url3]:
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
                        await client.log('[DEBUG TRACE] file removed\n', interaction)

                    if r.status_code == 200:
                        with open('output.mp4', 'wb') as f:
                            f.write(r.content)
                        await client.log('[DEBUG TRACE] video downloaded\n', interaction)

                        # file validation, checks video codecs with ffmpeg and converts to mp4 if bitstream is hvec
                        os.system("ffprobe -loglevel quiet -select_streams v -show_entries stream=codec_name -of default=nw=1:nk=1 output.mp4 > log.txt 2>&1")
                        log_file = open("log.txt","r")
                        log_file_content = log_file.read()
                        await client.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}\n', interaction)

                        try:
                            await client.generic_output(interaction, link=link, spoilerwarning=spoilerwarning)
                            if header: await interaction.channel.send(header)
                            await interaction.channel.send(fulldesc)
                            await client.log('[DEBUG TRACE] file sent\n', interaction)
                            client.lastlink = link
                        except discord.HTTPException as e:
                            if e.code == 40005:
                                await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                                if header: await interaction.channel.send(header)
                                await interaction.channel.send(fulldesc)
                            else:
                                raise
                    else:
                        await client.log(f'[DEBUG TRACE] Request failed with status code: {r.status_code}\n', interaction)
                        await client.handle_error(r.status_code, interaction, link=link)
        except Exception as e:
            await client.handle_error(e, interaction, link=link)
        finally:
            driver.quit()

    @client.tree.command(name = "withaudio", description = "Send tiktok with audio")
    async def with_audio(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
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
            await client.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', interaction)
            
            await client.log(f'[DEBUG TRACE] message detected: {link}\n', interaction)

            lst = link.split(' ')
            for word in lst:
                if '.tiktok.com/' in word:
                    if word.startswith("||") and word.endswith("||"): spoilerwarning = True #foolproofing
                    link = word.strip('||')

            await client.log(f'[DEBUG TRACE] extracted link: {link}\n', interaction)
            
            driver.get(link)

            # Run Prechecks
            try:
                maturecontent = WebDriverWait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'p')))
                for words in maturecontent:
                    if words.text == 'Log in to TikTok':
                        await client.log(f'[DEBUG TRACE] Mature content detected\n', interaction)
                        await interaction.followup.send(link)
                        await client.generic_message(interaction, "Mature Content Detected. Gotta go to the app for this one buddy", ephemeral=True)
                        return
            except:
                pass

            await client.log(f'[DEBUG TRACE] No mature content detected\n', interaction)

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
            
            await client.log(f'[DEBUG TRACE] Found username\n', interaction)

            music=None

            url = await client.find_video(driver, interaction)

            all_cookies = driver.get_cookies()
            cookies = {cookies['name']:cookies['value'] for cookies in all_cookies}

            if music: 
                try:
                    s = requests.get(music, cookies=cookies, headers=headers)

                    if os.path.exists('audio.wav'):
                        os.remove('audio.wav')
                        client.log('[DEBUG TRACE] audio file removed\n', interaction)

                    if s.status_code == 200:
                        with open('audio.wav', 'wb') as f:
                            f.write(s.content)
                        client.log('[DEBUG TRACE] audio downloaded\n', interaction)
                    else:
                        client.log(f'[DEBUG TRACE] Failed to download audio: {s.status_code}\n', interaction)
                        await client.handle_error(s.status_code, interaction, link=link)
                except OSError as e:
                    if str(e).startswith('No connection adapters were found for'):
                        client.log(f'[DEBUG TRACE] Blob link detected:  No connection adapters were found for {music}\n', interaction)
                        await client.generic_message(interaction, "Failed to get audio... (inaccessable file location)", ephemeral=True)
                    else:
                        raise

            if url is None:
                await client.process_slideshow(driver, interaction, headers, spoilerwarning, userinput=link)
                await interaction.channel.send(file=discord.File('audio.wav'))
                client.log('[DEBUG TRACE] audio file sent\n', interaction)

            else:
                r = requests.get(url, cookies=cookies, headers=headers)
                
                if os.path.exists('output.mp4'):
                    os.remove('output.mp4')
                    client.log('[DEBUG TRACE] file removed\n', interaction)

                if r.status_code == 200:
                    with open('output.mp4', 'wb') as f:
                        f.write(r.content)
                    client.log('[DEBUG TRACE] video downloaded\n', interaction)

                    # file validation, checks video codecs with ffmpeg and converts to mp4 if bitstream is hvec
                    os.system("ffprobe -loglevel quiet -select_streams v -show_entries stream=codec_name -of default=nw=1:nk=1 output.mp4 > log.txt 2>&1")
                    log_file = open("log.txt","r")
                    log_file_content = log_file.read()
                    client.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}\n', interaction)

                    try:
                        await client.generic_output(interaction, link=link, spoilerwarning=spoilerwarning)
                        client.log('[DEBUG TRACE] file sent\n', interaction)
                        client.lastlink = link
                    except discord.HTTPException as e:
                        if e.code == 40005:
                            await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                        else:
                            raise
                else:
                    client.log(f'[DEBUG TRACE] Failed to download video: {r.status_code}\n', interaction)
                    await client.handle_error(r.status_code, interaction, link=link)

            try:
                client.log(f'[DEBUG TRACE] checking for audio\n', interaction)
                newlink = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[aria-label*="Watch more videos with music"]'))).get_attribute('href')
                client.log(f'[DEBUG TRACE] found video music disc\n', interaction)
                driver.get(newlink)
                client.log(f'[DEBUG TRACE] navigated to site\n', interaction)
                music = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "video"))).get_attribute('src')
                client.log(f'[DEBUG TRACE] got music\n', interaction) 
            except:
                client.log(f'[DEBUG TRACE] failed to get music\n', interaction)
                await client.generic_message(interaction, "Failed to get audio...", ephemeral=True)

        except Exception as e:
            await client.handle_error(e, interaction, link=link)
        finally:
            driver.quit()

    @client.tree.command(name = "meow", description = "Send tiktok with description and audio")
    async def meow(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
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
            client.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', interaction)
            
            client.log(f'[DEBUG TRACE] message detected: {link}\n', interaction)

            lst = link.split(' ')
            for word in lst:
                if '.tiktok.com/' in word:
                    if word.startswith("||") and word.endswith("||"): spoilerwarning = True #foolproofing
                    link = word.strip('||')

            client.log(f'[DEBUG TRACE] extracted link: {link}\n', interaction)
            
            driver.get(link)

            # Run Prechecks
            try:
                maturecontent = WebDriverWait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'p')))
                for words in maturecontent:
                    if words.text == 'Log in to TikTok':
                        await client.log(f'[DEBUG TRACE] Mature content detected\n', interaction)
                        await interaction.followup.send(link)
                        await client.generic_message(interaction, "Mature Content Detected. Gotta go to the app for this one buddy", ephemeral=True)
                        return
            except:
                pass

            client.log(f'[DEBUG TRACE] No mature content detected\n', interaction)

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
            
            client.log(f'[DEBUG TRACE] Found username\n', interaction)

            meta = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "/html/head/meta[@property='og:description']")))
            desc = meta.get_attribute("content")

            client.log(f'[DEBUG TRACE] Found description\n', interaction)

            if len(desc)>2000:
                desc = desc[:1900] + "..."
                client.log(f'[DEBUG TRACE] Description shrunk\n', interaction)

            header=None

            try:
                header = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text
                header = '**' + header + '**'
                client.log(f'[DEBUG TRACE] Found header\n', interaction)
            except:
                pass

            fulldesc = '*' + username + ':* ' + desc

            music=None

            url = await client.find_video(driver, interaction)

            all_cookies = driver.get_cookies()
            cookies = {cookies['name']:cookies['value'] for cookies in all_cookies}

            if url is None:
                await client.process_slideshow(driver, interaction, headers, spoilerwarning, userinput=link)
                if header: await interaction.channel.send(header)
                await interaction.channel.send(fulldesc)

            else:
                r = requests.get(url, cookies=cookies, headers=headers)
                
                if os.path.exists('output.mp4'):
                    os.remove('output.mp4')
                    client.log(f'[DEBUG TRACE] file removed\n', interaction)

                if r.status_code == 200:
                    with open('output.mp4', 'wb') as f:
                        f.write(r.content)
                    client.log(f'[DEBUG TRACE] video downloaded\n', interaction)

                    # file validation, checks video codecs with ffmpeg and converts to mp4 if bitstream is hvec
                    os.system("ffprobe -loglevel quiet -select_streams v -show_entries stream=codec_name -of default=nw=1:nk=1 output.mp4 > log.txt 2>&1")
                    log_file = open("log.txt","r")
                    log_file_content = log_file.read()
                    client.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}\n', interaction)

                    try:
                        await client.generic_output(interaction, link=link, spoilerwarning=spoilerwarning)
                        if header: await interaction.channel.send(header)
                        await interaction.channel.send(fulldesc)
                        client.log(f'[DEBUG TRACE] file sent\n', interaction)
                        client.lastlink = link
                    except discord.HTTPException as e:
                        if e.code == 40005:
                            await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                            if header: await interaction.channel.send(header)
                            await interaction.channel.send(fulldesc)
                        else:
                            raise
                else:
                    client.log(f'[DEBUG TRACE] failed to download video\n', interaction)
                    await client.handle_error(r.status_code, interaction, link=link)

            try:
                client.log(f'[DEBUG TRACE] checking for audio\n', interaction)
                newlink = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[aria-label*="Watch more videos with music"]'))).get_attribute('href')
                client.log(f'[DEBUG TRACE] found video music disc\n', interaction)
                driver.get(newlink)
                client.log(f'[DEBUG TRACE] navigated to site\n', interaction)
                music = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "video"))).get_attribute('src')
                client.log(f'[DEBUG TRACE] got music\n', interaction)
            except:
                client.log(f'[DEBUG TRACE] failed to get music\n', interaction)
                await client.generic_message(interaction, "Failed to get audio...", ephemeral=True)
            if music: 
                try:
                    s = requests.get(music, cookies=cookies, headers=headers)

                    if os.path.exists('audio.wav'):
                        os.remove('audio.wav')
                        client.log(f'[DEBUG TRACE] audio file removed\n', interaction)

                    if s.status_code == 200:
                        with open('audio.wav', 'wb') as f:
                            f.write(s.content)
                        client.log(f'[DEBUG TRACE] audio downloaded\n', interaction)

                        await interaction.channel.send(file=discord.File('audio.wav'))

                        client.log(f'[DEBUG TRACE] audio file sent\n', interaction)

                    else:
                        client.log(f'[DEBUG TRACE] failed to download audio\n', interaction)
                        await client.handle_error(s.status_code, interaction, link=link)
                except OSError as e:
                    if str(e).startswith('No connection adapters were found for'):
                        client.log(f'[DEBUG TRACE] Blob link detected:  No connection adapters were found for {music}\n', interaction)
                        await client.generic_message(interaction, "Failed to get audio... (inaccessable file location)", ephemeral=True)
                    else:
                        raise
        except Exception as e:
            await client.handle_error(e, interaction, link=link)
        finally:
            driver.quit()