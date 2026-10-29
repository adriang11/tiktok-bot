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
from selenium.common.exceptions import StaleElementReferenceException
from bot import client
from bot.data.statics import headers
from bot.data.statics import no_free_views
from bot.utils.driver import create_driver
from bot.utils.validation import validate_file
from toolz import get_in
from typing import Literal


def register(client):
    @client.tree.command(name = "sugma", description = "Send tiktok without description")
    async def sugma(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
        await interaction.response.defer()
        
        spoilerwarning = spoilered == "true"

        async with client.scrape_lock:
            driver = create_driver(headers, block_images=True)

            try:
                await client.web_scrape(driver, interaction, headers, spoilerwarning, userinput=link)
            except Exception as e:
                await client.log(f'[DEBUG TRACE] Standard error detected: {e}\n', interaction)
                await client.handle_error(e, interaction, link=link)
            finally:
                await client.log(f'[DEBUG TRACE] closing session', interaction)
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception as e:
                        await client.log(f'[DEBUG TRACE] Error closing session: {e}\n',interaction)

    @client.tree.command(name = "override", description = "Send tiktok overriding no free views")
    async def override(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
        if interaction.user.id != 474713843181027328:
            await interaction.response.send_message("You are not Adrian.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        spoilerwarning = spoilered == "true"

        async with client.scrape_lock:
            driver = create_driver(headers, block_images=True)

            try:
                await client.web_scrape(driver, interaction, headers, spoilerwarning, userinput=link, override=True)
            except Exception as e:
                await client.log(f'[DEBUG TRACE] Standard error detected: {e}\n', interaction)
                await client.handle_error(e, interaction, link=link)
            finally:
                await client.log(f'[DEBUG TRACE] closing session', interaction)
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception as e:
                        await client.log(f'[DEBUG TRACE] Error closing session: {e}\n',interaction)

    @client.tree.command(name = "withcaption", description = "Send tiktok with description")
    async def with_caption(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
        await interaction.response.defer()
        
        spoilerwarning = spoilered == "true"

        async with client.scrape_lock:
            driver = create_driver(headers, block_images=True)

            try:
                await client.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', interaction)
                
                await client.log(f'[DEBUG TRACE] message detected: {link}\n', interaction)

                lst = link.split(' ')
                for word in lst:
                    if '.tiktok.com/' in word or '.tt.site/' in word:
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

                username = await client.get_tiktok_username(driver, interaction)
                
                if username is None:
                    await client.log(f"[DEBUG TRACE] Could not determine posting username. URL={driver.current_url!r}\n", interaction)
        
                    #raise RuntimeError("Unable to determine TikTok posting account")
                    username = "Unknown"
        
                await client.log(f"[DEBUG TRACE] Posting account: @{username}\n", interaction)
                
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

                    await client.log(f'[DEBUG TRACE] closing session\n', interaction)
                    driver.quit()
                    driver =None

                    r = requests.get(url, cookies=cookies, headers=headers)
                    
                    if os.path.exists('output.mp4'):
                        os.remove('output.mp4')
                        await client.log('[DEBUG TRACE] file removed\n', interaction)

                    if r.status_code == 200:
                        with open('output.mp4', 'wb') as f:
                            f.write(r.content)
                        await client.log('[DEBUG TRACE] video downloaded\n', interaction)
                        
                        log_file_content = validate_file()
                        
                        await client.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}', interaction)
                        if log_file_content == "":  
                            await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                            if header: await interaction.channel.send(header)
                            await interaction.channel.send(fulldesc)
                        else:
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
                await client.log(f'[DEBUG TRACE] closing session', interaction)
                driver.quit()

    @client.tree.command(name = "candice", description = "for dev testing: sends 3 CDN url links shortened")
    async def candice(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
        await interaction.response.defer()

        spoilerwarning = spoilered == "true"

        async with client.scrape_lock:
            driver = create_driver(headers, block_images=True)

            try:
                await client.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', interaction)
                
                await client.log(f'[DEBUG TRACE] message detected: {link}\n', interaction)

                lst = link.split(' ')
                for word in lst:
                    if '.tiktok.com/' in word or '.tt.site/' in word:
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

                username = await client.get_tiktok_username(driver, interaction)
                                
                if username is None:
                    await client.log(f"[DEBUG TRACE] Could not determine posting username. URL={driver.current_url!r}\n", interaction)
        
                    #raise RuntimeError("Unable to determine TikTok posting account")
                    username = "Unknown"
        
                await client.log(f"[DEBUG TRACE] Posting account: @{username}\n", interaction)
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
                    
                    script_tag = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(
                            (By.ID, "__UNIVERSAL_DATA_FOR_REHYDRATION__")
                        )
                    )

                    raw_data = script_tag.get_attribute("textContent")
                    data = json.loads(raw_data)

                    video_path = [
                        "__DEFAULT_SCOPE__",
                        "webapp.video-detail",
                        "itemInfo",
                        "itemStruct",
                        "video",
                        "bitrateInfo",
                        0,
                        "PlayAddr",
                        "UrlList",
                    ]

                    play_urls = get_in(video_path, data, [])
                    url1 = play_urls[2] if len(play_urls) > 2 else None
                    url2 = play_urls[1] if len(play_urls) > 1 else None
                    url3 = play_urls[0] if play_urls else None

                    del data, raw_data

                
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

                        await client.log(f'[DEBUG TRACE] closing session\n', interaction)
                        driver.quit()
                        driver =None

                        r = requests.get(url, cookies=cookies, headers=headers)
                        
                        if os.path.exists('output.mp4'):
                            os.remove('output.mp4')
                            await client.log('[DEBUG TRACE] file removed\n', interaction)

                        if r.status_code == 200:
                            with open('output.mp4', 'wb') as f:
                                f.write(r.content)
                            await client.log('[DEBUG TRACE] video downloaded\n', interaction)

                            log_file_content = validate_file()
                        
                            await client.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}', interaction)
                            if log_file_content == "":  
                                await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                            else:
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
                await client.log(f'[DEBUG TRACE] closing session', interaction)
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception as e:
                        await client.log(f'[DEBUG TRACE] Error closing session: {e}\n',interaction)

    @client.tree.command(name = "withaudio", description = "Send tiktok with audio")
    async def with_audio(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
        await interaction.response.defer()
        
        spoilerwarning = spoilered == "true"

        async def fail_audio(reason):
            await client.log(f"[DEBUG TRACE] Audio retrieval failed: {reason}\n",interaction)

            # Replace the deferred response with the original link.
            await interaction.edit_original_response(content=link)

            # One private error message.
            await interaction.followup.send("Failed to get audio...",ephemeral=True)

        async with client.scrape_lock:
            driver = create_driver(headers, block_images=True)

            try:
                await client.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', interaction)
                
                await client.log(f'[DEBUG TRACE] message detected: {link}\n', interaction)

                lst = link.split(' ')
                for word in lst:
                    if '.tiktok.com/' in word or '.tt.site/' in word:
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

                username = await client.get_tiktok_username(driver, interaction)
                                
                if username is None:
                    await client.log(f"[DEBUG TRACE] Could not determine posting username. URL={driver.current_url!r}\n", interaction)
        
                    #raise RuntimeError("Unable to determine TikTok posting account")
                    username = "Unknown"
        
                await client.log(f"[DEBUG TRACE] Posting account: @{username}\n", interaction)
                if username in no_free_views:
                    await interaction.followup.send(link)
                    await interaction.followup.send("No free views", ephemeral=True)
                    return
                
                await client.log(f'[DEBUG TRACE] Found username\n', interaction)

                music = None

                url = await client.find_video(driver, interaction)

                all_cookies = driver.get_cookies()
                cookies = {c["name"]: c["value"] for c in all_cookies}

                try:
                    await client.log("[DEBUG TRACE] Checking for audio\n", interaction)

                    # Read the music link directly from the DOM.
                    newlink = WebDriverWait(driver, 5).until(
                        lambda d: d.execute_script("""
                            const link = document.querySelector(
                                'a[aria-label*="Watch more videos with music"]'
                            );
                            return link ? link.href : null;
                        """)
                    )

                    if not newlink:
                        raise ValueError("Music link has no href")

                    await client.log("[DEBUG TRACE] Found video music link\n", interaction)

                    driver.get(newlink)

                    # Retry locating the video if TikTok replaces the DOM element.
                    music = WebDriverWait(driver,10,ignored_exceptions=[StaleElementReferenceException]).until(
                        lambda d: d.execute_script("""
                            const video = document.querySelector("video");
                            return video ? video.getAttribute("src") : null;
                        """)
                    )

                    if not music or music.startswith("blob:"):
                        raise ValueError(f"Music source is empty or browser-only: {music}")

                    await client.log("[DEBUG TRACE] Got audio URL\n",interaction)

                except Exception as e:
                    await fail_audio(f"Could not extract audio URL: {e}")
                    return

                try:
                    if os.path.exists("audio.wav"):
                        os.remove("audio.wav")

                    s = requests.get(
                        music,
                        cookies=cookies,
                        headers=headers,
                        timeout=(5, 20)
                    )

                    if s.status_code != 200 or not s.content:
                        await fail_audio(
                            f"Audio download returned HTTP {s.status_code}"
                        )
                        return

                    with open("audio.wav", "wb") as f:
                        f.write(s.content)

                    await client.log(
                        "[DEBUG TRACE] Audio downloaded\n", interaction
                    )

                except Exception as e:
                    await fail_audio(f"Audio download failed: {e}")
                    return

                if url is None:
                    driver.get(link)
                    await client.process_slideshow(driver, interaction, headers, spoilerwarning, userinput=link)
                    await interaction.channel.send(file=discord.File('audio.wav'))
                    await client.log('[DEBUG TRACE] audio file sent\n', interaction)

                else:
                    r = requests.get(url, cookies=cookies, headers=headers)
                    
                    if os.path.exists('output.mp4'):
                        os.remove('output.mp4')
                        await client.log('[DEBUG TRACE] file removed\n', interaction)

                    if r.status_code == 200:
                        with open('output.mp4', 'wb') as f:
                            f.write(r.content)
                        await client.log('[DEBUG TRACE] video downloaded\n', interaction)

                        log_file_content = validate_file()
                        
                        await client.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}', interaction)
                        if log_file_content == "":  
                            await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                            await interaction.channel.send(file=discord.File('audio.wav'))
                            await client.log(f'[DEBUG TRACE] audio file sent\n', interaction)
                        else:
                            try:
                                await client.generic_output(interaction, link=link, spoilerwarning=spoilerwarning)
                                await client.log('[DEBUG TRACE] file sent\n', interaction)
                                client.lastlink = link
                                await interaction.channel.send(file=discord.File('audio.wav'))
                                await client.log(f'[DEBUG TRACE] audio file sent\n', interaction)
                            except discord.HTTPException as e:
                                if e.code == 40005:
                                    await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                                    await interaction.channel.send(file=discord.File('audio.wav'))
                                    await client.log(f'[DEBUG TRACE] audio file sent\n', interaction)
                                else:
                                    raise
                    else:
                        await client.log(f'[DEBUG TRACE] Failed to download video: {r.status_code}\n', interaction)
                        await client.handle_error(r.status_code, interaction, link=link)
            except:
                await client.log('[DEBUG TRACE] failed to get music\n', interaction)
                await client.generic_message(interaction, "Failed to get audio...", ephemeral=True)

    @client.tree.command(name = "meow", description = "Send tiktok with description and audio")
    async def meow(interaction: discord.Interaction, link: str, spoilered: Literal["true", "false"] = "false"):
        await interaction.response.defer()
        
        spoilerwarning = spoilered == "true"

        async with client.scrape_lock:

            driver = create_driver(headers, block_images=True)

            try:
                await client.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', interaction)
                
                await client.log(f'[DEBUG TRACE] message detected: {link}\n', interaction)

                lst = link.split(' ')
                for word in lst:
                    if '.tiktok.com/' in word or '.tt.site/' in word:
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

                username = await client.get_tiktok_username(driver, interaction)
                                
                if username is None:
                    await client.log(f"[DEBUG TRACE] Could not determine posting username. URL={driver.current_url!r}\n", interaction)
        
                    #raise RuntimeError("Unable to determine TikTok posting account")
                    username = "Unknown"
        
                await client.log(f"[DEBUG TRACE] Posting account: @{username}\n", interaction)
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

                url = await client.find_video(driver, interaction)

                all_cookies = driver.get_cookies()
                cookies = {cookies['name']:cookies['value'] for cookies in all_cookies}

                music = None
                audio_downloaded = False
                audio_error_sent = False

                # Remove any previous audio file so a failed request
                # cannot accidentally send audio from an earlier request.
                if os.path.exists("audio.wav"):
                    os.remove("audio.wav")
                    await client.log("[DEBUG TRACE] Removed previous audio file\n", interaction)

                async def report_audio_failure(reason):
                    nonlocal audio_error_sent

                    await client.log(
                        f"[DEBUG TRACE] Audio retrieval failed: {reason}\n", interaction)

                    if not audio_error_sent:
                        audio_error_sent = True
                        await client.generic_message(interaction,"Failed to get audio...",ephemeral=True)

                # Extract the music URL.
                try:
                    await client.log("[DEBUG TRACE] Checking for audio\n",interaction)

                    newlink = WebDriverWait(driver, 5).until(
                        lambda d: d.execute_script("""
                            const link = document.querySelector(
                                'a[aria-label*="Watch more videos with music"]'
                            );
                            return link ? link.href : null;
                        """)
                    )

                    if not newlink:
                        raise ValueError("Music link not found")

                    await client.log("[DEBUG TRACE] Found video music disc\n",interaction)

                    driver.get(newlink)

                    await client.log("[DEBUG TRACE] Navigated to music page\n",interaction)

                    music = WebDriverWait(driver, 8).until(
                        lambda d: d.execute_script("""
                            const video = document.querySelector("video");
                            if (!video) return null;

                            const src = video.currentSrc || video.src;
                            return src || null;
                        """)
                    )

                    if not music or music.startswith("blob:"):
                        raise ValueError(
                            f"Audio source is missing or browser-only: {music!r}"
                        )

                    await client.log("[DEBUG TRACE] Got music URL\n",interaction)

                except Exception as e:
                    await report_audio_failure(f"Could not extract music URL: {type(e).__name__}: {e}")
                    music = None

                # Download audio only if extraction succeeded.
                if music:
                    try:
                        s = requests.get(
                            music,
                            cookies=cookies,
                            headers=headers,
                            timeout=(5, 20)
                        )

                        if s.status_code != 200 or not s.content:
                            raise ValueError(f"Audio download returned HTTP {s.status_code}")

                        with open("audio.wav", "wb") as f:
                            f.write(s.content)

                        audio_downloaded = True

                        await client.log("[DEBUG TRACE] Audio downloaded successfully\n",interaction)

                    except Exception as e:
                        # A partial/invalid download must not be sent.
                        if os.path.exists("audio.wav"):
                            os.remove("audio.wav")

                        await report_audio_failure(f"Audio download error: {type(e).__name__}: {e}")


                if url is None:
                    driver.get(link)

                    await client.process_slideshow(driver,interaction,headers,spoilerwarning,userinput=link)
                    if header: await interaction.channel.send(header)
                    await interaction.channel.send(fulldesc)

                    if audio_downloaded and os.path.exists("audio.wav"):
                        await interaction.channel.send(file=discord.File("audio.wav"))
                        await client.log("[DEBUG TRACE] Audio file sent\n",interaction)
                    else:
                        await client.log("[DEBUG TRACE] Skipping audio attachment; audio retrieval failed\n",interaction)

                else:
                    r = requests.get(url, cookies=cookies, headers=headers)

                    await client.log(f'[DEBUG TRACE] closing session\n', interaction)
                    driver.quit()
                    driver =None
                    
                    if os.path.exists('output.mp4'):
                        os.remove('output.mp4')
                        await client.log(f'[DEBUG TRACE] file removed\n', interaction)

                    if r.status_code == 200:
                        with open('output.mp4', 'wb') as f:
                            f.write(r.content)
                        await client.log(f'[DEBUG TRACE] video downloaded\n', interaction)

                        log_file_content = validate_file()
                        
                        await client.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}', interaction)
                        if log_file_content == "":  
                            await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                            await interaction.channel.send(fulldesc)
                            await client.log(f'[DEBUG TRACE] file sent\n', interaction)
                            await interaction.channel.send(file=discord.File('audio.wav'))
                            await client.log(f'[DEBUG TRACE] audio file sent\n', interaction)
                        else:
                            try:
                                await client.generic_output(interaction, link=link, spoilerwarning=spoilerwarning)
                                if header: await interaction.channel.send(header)
                                await interaction.channel.send(fulldesc)
                                await client.log(f'[DEBUG TRACE] file sent\n', interaction)
                                await interaction.channel.send(file=discord.File('audio.wav'))
                                await client.log(f'[DEBUG TRACE] audio file sent\n', interaction)
                                client.lastlink = link
                            except discord.HTTPException as e:
                                if e.code == 40005:
                                    await client.handle_large_upload(interaction, url, spoilerwarning=spoilerwarning)
                                    if header: await interaction.channel.send(header)
                                    await interaction.channel.send(fulldesc)
                                    await interaction.channel.send(file=discord.File('audio.wav'))
                                    await client.log(f'[DEBUG TRACE] audio file sent\n', interaction)    
                                else:
                                    raise
                    else:
                        await client.log(f'[DEBUG TRACE] failed to download video\n', interaction)
                        await client.handle_error(r.status_code, interaction, link=link)

            except Exception as e:
                await client.handle_error(e, interaction, link=link)
            finally:
                await client.log(f'[DEBUG TRACE] closing session', interaction)
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception as e:
                        await client.log(f'[DEBUG TRACE] Error closing session: {e}\n',interaction)