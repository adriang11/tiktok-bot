import asyncio
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
from selenium.common.exceptions import WebDriverException
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
from urllib.parse import urlparse, parse_qs
import re

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
        self.scrape_lock = asyncio.Lock()
    
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

    async def breakpoint(self, driver, ctx):
        if self.screencap: 
            driver.get_screenshot_as_file("screenshot.png")
            await ctx.channel.send(file=discord.File('screenshot.png'))

    async def handle_large_upload(self, ctx, cdn_url, link, spoilerwarning=False):
        self.lastlink = "" # Do not store video if large file
        try:   
            # headers = {
            #     "Authorization": f"Bearer {TINYURL_KEY}",
            #     "Content-Type": "application/json"
            # }

            # r = requests.post(
            #     "https://api.tinyurl.com/create",
            #     headers=headers,
            #     json={"url": cdn_url},
            #     timeout=10
            # )
            
            # r.raise_for_status()

            # short = r.json()["data"]["tiny_url"]
            
            # await self.log(f"[DEBUG TRACE] Shortener Response: {short}\n", ctx)

            # final_url = short if short else cdn_url
            s = pyshorteners.Shortener(api_key=SHORTIO_KEY, domain='chungus.s.gy')
            final_url = s.shortcm.short(cdn_url)
            await self.log(f"[DEBUG TRACE] shortened URL: {final_url}\n", ctx)

        except Exception as e:
            await self.log(f"[DEBUG TRACE] URL shortening failed: {e}\n", ctx)
            final_url = cdn_url
        
        if spoilerwarning: final_url= f"||{final_url}||"

        if isinstance(ctx, discord.Message):
            await ctx.reply(final_url)
            await self.log(f"[DEBUG TRACE] file sent", ctx)
        elif isinstance(ctx, discord.Interaction):
            await ctx.followup.send('<' + link + '>')
            await ctx.channel.send(final_url)
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
            await send_response('I can\'t get this shit to work I\'m sorry. I\'m fucking sorry. Only videos for now. Check /serverstatus for updates.')
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
                # Silent error, try again later
                if isinstance(ctx, discord.Message):
                    return await ctx.reply('Rate Limited (They\'re onto us) Please try again in a moment', mention_author=True, delete_after=30)
                elif isinstance(ctx, discord.Interaction):
                    return await ctx.followup.send('Rate Limited (They\'re onto us) Please try again in a moment', ephemeral=True)
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

    async def get_tiktok_username(self, driver, ctx):
        """Return the posting username, or None if it cannot be determined."""

        candidates = []

        # Read the redirected URL.
        try:
            candidates.append(("driver.current_url", driver.current_url))
        except WebDriverException as e:
            await self.log(f"[DEBUG TRACE] Failed to read current URL: {e}\n", ctx)

        # Read relevant metadata without copying the full page source.
        try:
            metadata = driver.execute_script("""
                const getMeta = (selector) =>
                    document.querySelector(selector)?.content || "";

                return {
                    ogUrl: getMeta('meta[property="og:url"]'),
                    canonical: document.querySelector(
                        'link[rel="canonical"]'
                    )?.href || ""
                };
            """)

            candidates.insert(0, ("og:url", metadata.get("ogUrl", "")))
            candidates.insert(1, ("canonical", metadata.get("canonical", "")))

        except WebDriverException as e:
            await self.log(f"[DEBUG TRACE] Failed to retrieve URL metadata: {e}\n", ctx)

        # Try each candidate in priority order.
        for source, candidate in candidates:
            if not candidate:
                await self.log(f"[DEBUG TRACE] Username lookup: {source} is empty\n", ctx)
                continue

            try:
                path = urlparse(candidate).path
            except ValueError as e:
                await self.log(f"[DEBUG TRACE] Username lookup: invalid URL from {source}: {candidate!r} ({e})\n", ctx)
                continue

            parts = path.split("/")

            for i, part in enumerate(parts[:-1]):
                if part.startswith("@") and len(part) > 1:
                    if parts[i + 1]  in ("video", "photo"):
                        username = part[1:]

                        await self.log(f"[DEBUG TRACE] Username lookup: found @{username} from {source} \n", ctx)
                        return username

            await self.log(f"[DEBUG TRACE] Username lookup: no username found in {source} (URL= <{candidate!r}> )\n", ctx)

        await self.log("[DEBUG TRACE] Username lookup: no candidate contained a recognizable TikTok username\n", ctx)

        return None

    async def run_prechecks(self, driver, ctx, spoilerwarning, *, userinput=None, override=False):
        if isinstance(ctx, discord.Message):
            link = ctx.content
        elif isinstance(ctx, discord.Interaction):
            link = userinput
        
        await self.log(f'[DEBUG TRACE] message detected: <{link}>\n', ctx)

        if link == self.lastlink:
            await self.log(f'[DEBUG TRACE] last link matched: <{link}>\n', ctx)
            await self.generic_output(ctx, link=link, spoilerwarning=spoilerwarning)
            return
        
        # strip link from message if appicable
        lst = link.split(' ')
        for word in lst:
            if '.tiktok.com/' in word:
                if word.startswith("||") and word.endswith("||"): spoilerwarning = True #foolproofing
                link = word.strip('||')

        await self.log(f'[DEBUG TRACE] extracted link: <{link}>\n', ctx)

        await self.log(f'[DEBUG TRACE] clearing tmp files\n', ctx)
        if os.path.exists('output.mp4'):
            os.remove('output.mp4')
            await self.log('[DEBUG TRACE] video file removed\n', ctx)
        if os.path.exists('audio.wav'):
            os.remove('audio.wav')
            await self.log('[DEBUG TRACE] audio file removed\n', ctx)


        self.debug_tiktok_cookies(driver, "BEFORE NAVIGATION")

        await self.log(f'[DEBUG TRACE] starting chrome\n', ctx)
        driver.get(link)

        self.debug_tiktok_cookies(driver, "BEFORE RELOAD")

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

        # await self.breakpoint(driver, ctx)

        username = await self.get_tiktok_username(driver, ctx)

        if username is None:
            await self.log(f"[DEBUG TRACE] Could not determine posting username. URL= <{driver.current_url!r}> \n", ctx)

            #raise RuntimeError("Unable to determine TikTok posting account")
            username = "Unknown"

        await self.log(f"[DEBUG TRACE] Posting account: @{username}\n", ctx)

        if username in no_free_views:
            if isinstance(ctx, discord.Message):
                await ctx.reply("No free views")
            elif isinstance(ctx, discord.Interaction):
                await ctx.followup.send(link)
                await ctx.followup.send("No free views", ephemeral=True)
            return
            
        await self.log(f'[DEBUG TRACE] View stealing protected\n', ctx)

        return link

    def debug_tiktok_cookies(self, driver, label=""):
        try:
            cookies = driver.execute_cdp_cmd("Network.getAllCookies", {}).get("cookies", [])

            matches = [
                cookie for cookie in cookies
                if "msToken".lower() in cookie.get("name", "").lower()
            ]

            print(f"\n========== {label} COOKIE DIAGNOSTICS ==========")
            print(f"Total browser cookies: {len(cookies)}")
            print(f"msToken cookies found: {len(matches)}")

            for cookie in matches:
                print({
                    "name": cookie.get("name"),
                    "length": len(cookie.get("value", "")),
                    "domain": cookie.get("domain"),
                    "path": cookie.get("path"),
                    "secure": cookie.get("secure"),
                    "httpOnly": cookie.get("httpOnly"),
                    "expires": cookie.get("expires")
                })

            print("===============================================\n")

        except Exception as e:
            print(f"[DEBUG] Cookie inspection failed: {e}")
    
    async def find_video(self, driver, ctx):
        try:
            await self.log('[DEBUG TRACE] Searching for video in metadata\n', ctx)

            # Retrieve embedded JSON, not the video player
            raw_data = WebDriverWait(driver, 5).until(
                lambda d: (
                    d.find_element(
                        By.ID,
                        "__UNIVERSAL_DATA_FOR_REHYDRATION__"
                    ).get_attribute("textContent") or None
                )
            )

            # Parse only the embedded JSON instead of the entire page.
            data = json.loads(raw_data)
            del raw_data

            item_struct = get_in(["__DEFAULT_SCOPE__","webapp.video-detail","itemInfo","itemStruct"],data)

            if not isinstance(item_struct, dict):
                await self.log("[DEBUG TRACE] itemStruct missing. Checking for TikTok slideshow\n", ctx)
                return None

            video_data = item_struct.get("video")

            if not isinstance(item_struct, dict) or not video_data:
                await self.log(f"[DEBUG TRACE] No video metadata found. Checking for TikTok slideshow\n", ctx)
                return None

            # await self.log(f"[DEBUG TRACE] itemStruct keys: {list(item_struct.keys())}\n",ctx)

            try: 
                video_format = get_in(["video", "bitrateInfo", 0, "Format"],item_struct)

                await self.log(f"[DEBUG TRACE] video format: {video_format}\n",ctx)

                if video_format == "dash":
                    play_url = get_in(["video", "PlayAddrStruct", "UrlList", 0],item_struct)
                else:
                    play_url = get_in(["video", "bitrateInfo", 0, "PlayAddr", "UrlList", 2],item_struct)
              
            except:
                await self.log("[DEBUG TRACE] No video metadata found. Checking for TikTok slideshow\n",ctx)
                play_url = None

            if play_url:
                await self.log("[DEBUG TRACE] CDN URL extracted\n",ctx)

                return {
                    "type": "video",
                    "url": play_url
                }

            await self.log("[DEBUG TRACE] Video metadata found, but no playable URL was extracted. Checking for TikTok slideshow\n",ctx)

            return None

        except TimeoutException as e:
            await self.log(f"[DEBUG TRACE] No TikTok metadata found {e.msg}\n",ctx)

            return None
        

    
    async def find_slideshow_images(self, driver, ctx):
        await self.log("[DEBUG TRACE] Jarvis, Initiate TikTok Photos Protocol\n",ctx)

        # Identify the post from the current URL.
        resolved_url = driver.current_url
        match = re.search(r"/(?:photo|video)/(\d+)", urlparse(resolved_url).path)

        if not match:
            await self.log("[DEBUG TRACE] Could not identify TikTok item ID\n", ctx)
            return []

        item_id = match.group(1)

        # Warm up TikTok to establish a browser session and obtain msToken.
        driver.get("https://www.tiktok.com/")

        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        time.sleep(3)

        cookies = {
            cookie["name"]: cookie["value"]
            for cookie in driver.get_cookies()
        }

        ms_token = cookies.get("msToken")

        await self.log(
            f"[DEBUG TRACE] TikTok session initialized. "
            f"msToken present: {bool(ms_token)}\n",
            ctx
        )

        # Clear homepage events so we only capture the photo request.
        try:
            driver.get_log("performance")
        except Exception:
            pass

        driver.get(resolved_url)

        await self.log(f"[DEBUG TRACE] Reloaded item {item_id}: {driver.current_url}\n",ctx)

        def capture_item_detail(driver, target_item_id, timeout=20):
            """Capture the matching item/detail response and its body."""

            pending = {}
            deadline = time.monotonic() + timeout

            while time.monotonic() < deadline:
                try:
                    logs = driver.get_log("performance")
                except Exception:
                    time.sleep(0.1)
                    continue

                for entry in logs:
                    try:
                        message = json.loads(entry["message"])["message"]
                    except (KeyError, TypeError, json.JSONDecodeError):
                        continue

                    method = message.get("method")
                    params = message.get("params", {})
                    request_id = params.get("requestId")

                    if method == "Network.requestWillBeSent":
                        request = params.get("request", {})
                        url = request.get("url", "")

                        if "/api/item/detail/" not in url:
                            continue

                        query = parse_qs(
                            urlparse(url).query,
                            keep_blank_values=True
                        )

                        requested_id = query.get("itemId", [None])[0]

                        if requested_id != str(target_item_id):
                            continue

                        pending[request_id] = {
                            "item_id": requested_id,
                            "request_url": url,
                            "url_path": urlparse(url).path,
                            "msToken_length": len(
                                query.get("msToken", [""])[0]
                            ),
                            "x_bogus": query.get("X-Bogus", [None])[0],
                            "response_received": False,
                            "loading_finished": False,
                            "body_retrieved": False
                        }

                    elif request_id in pending:
                        info = pending[request_id]

                        if method == "Network.responseReceived":
                            response = params.get("response", {})

                            info.update({
                                "response_received": True,
                                "status": response.get("status"),
                                "mime_type": response.get("mimeType")
                            })

                        elif method == "Network.loadingFinished":
                            info["loading_finished"] = True

                            try:
                                result = driver.execute_cdp_cmd(
                                    "Network.getResponseBody",
                                    {"requestId": request_id}
                                )

                                body = result.get("body", "")

                                if result.get("base64Encoded"):
                                    body = base64.b64decode(body).decode(
                                        "utf-8",
                                        errors="replace"
                                    )

                                info["body_length"] = len(body)
                                info["body_retrieved"] = True

                                try:
                                    data = json.loads(body)
                                    info["json_valid"] = True
                                    info["has_data"] = bool(
                                        data.get("itemInfo")
                                        or data.get("itemStruct")
                                        or data.get("item_info")
                                    )
                                except (json.JSONDecodeError, AttributeError, TypeError):
                                    info["json_valid"] = False
                                    info["has_data"] = False

                            except Exception as exc:
                                info["body_error"] = str(exc)

                            return info

                        elif method == "Network.loadingFailed":
                            info.update({
                                "loading_failed": True,
                                "error_text": params.get("errorText")
                            })
                            return info

                time.sleep(0.1)

            if pending:
                return next(reversed(pending.values()))

            return {
                "target_request_seen": False,
                "item_id": str(target_item_id)
            }

        def retry_item_detail_with_signature(driver, request_url):
            """Retry item/detail with TikTok's browser-generated X-Bogus."""

            driver.set_script_timeout(30)

            return driver.execute_async_script("""
                const requestUrl = arguments[0];
                const done = arguments[arguments.length - 1];

                (async () => {
                    try {
                        const sdk = window.byted_acrawler;

                        if (typeof sdk?.frontierSign !== "function") {
                            throw new Error("frontierSign is unavailable");
                        }

                        // Remove the original fallback X-Bogus=1.
                        const [baseUrl, rawQuery = ""] = requestUrl.split("?", 2);

                        const params = rawQuery
                            .split("&")
                            .filter(p => !/^X-Bogus=/i.test(p));

                        const unsignedUrl = baseUrl +
                            (params.length ? "?" + params.join("&") : "");

                        // IMPORTANT: Pass the URL STRING, not {url: unsignedUrl}.
                        const result = await sdk.frontierSign(unsignedUrl);

                        const signature = result?.["X-Bogus"];

                        if (
                            typeof signature !== "string" ||
                            !signature ||
                            signature === "1"
                        ) {
                            throw new Error(
                                "Invalid X-Bogus result. Returned keys: " +
                                Object.keys(result || {}).join(", ")
                            );
                        }

                        const signedUrl = unsignedUrl +
                            (unsignedUrl.includes("?") ? "&" : "?") +
                            "X-Bogus=" + encodeURIComponent(signature);

                        const response = await fetch(signedUrl, {
                            method: "GET",
                            credentials: "include",
                            headers: {
                                "Accept": "application/json, text/plain, */*"
                            }
                        });

                        const body = await response.text();

                        done({
                            success: true,
                            status: response.status,
                            contentType: response.headers.get("content-type"),
                            signatureLength: signature.length,
                            bodyLength: body.length,
                            body: body
                        });

                    } catch (error) {
                        done({
                            success: false,
                            error: String(error)
                        });
                    }
                })();
            """, request_url)

        
        api_result = capture_item_detail(driver, item_id)

        if (
            api_result
            and api_result.get("body_length", 0) == 0
            and api_result.get("request_url")
        ):
            await self.log(
                "[DEBUG TRACE] Original API response was empty. "
                "Retrying with browser-generated X-Bogus...\n",
                ctx
            )

            retry_result = retry_item_detail_with_signature(
                driver,
                api_result["request_url"]
            )

            if retry_result.get("success"):
                await self.log(
                    "[DEBUG TRACE] Signed API retry:\n"
                    + json.dumps({
                        "status": retry_result.get("status"),
                        "content_type": retry_result.get("contentType"),
                        "signature_length": retry_result.get("signatureLength"),
                        "body_length": retry_result.get("bodyLength"),
                        "body_preview": retry_result.get("body", "")[:5000]
                    }, indent=2)
                    + "\n",
                    ctx
                )

                # Keep the successful response available for future
                # slideshow extraction from the API instead of the DOM.
                if retry_result.get("body"):
                    try:
                        api_result["json_data"] = json.loads(
                            retry_result["body"]
                        )
                    except json.JSONDecodeError:
                        pass

            else:
                await self.log(
                    "[DEBUG TRACE] Signed API retry failed: "
                    + retry_result.get("error", "Unknown error")
                    + "\n",
                    ctx
                )

        api_summary = {
            key: api_result.get(key)
            for key in (
                "item_id",
                "url_path",
                "msToken_length",
                "x_bogus",
                "status",
                "mime_type",
                "body_length",
                "json_valid",
                "has_data",
                "body_error"
            )
            if key in api_result
        }

        await self.log(
            "[DEBUG TRACE] Item detail API:\n"
            + json.dumps(api_summary, indent=2)
            + "\n",
            ctx
        )

        # Wait for the page to finish loading.
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        time.sleep(5)

        # Check whether the photo post actually rendered.
        diagnostics = driver.execute_script("""
            const images = Array.from(document.images);

            return {
                url: location.href,
                image_count: images.length,
                loaded_images: images.filter(
                    img => img.complete && img.naturalWidth > 0
                ).length,
                swiper_count: document.querySelectorAll(
                    ".swiper-wrapper"
                ).length,
                video_count: document.querySelectorAll("video").length,
                body_text: document.body.innerText.substring(0, 200)
            };
        """)

        await self.log(
            "[DEBUG TRACE] Photo DOM:\n"
            + json.dumps(diagnostics, indent=2)
            + "\n",
            ctx
        )

        # Wait for the slideshow wrapper.
        try:
            await self.breakpoint(driver, ctx)

            WebDriverWait(
                driver,
                15,
                0.5,
                (StaleElementReferenceException,)
            ).until(
                lambda d: d.find_element(
                    By.CSS_SELECTOR,
                    ".swiper-wrapper"
                )
            )

        except TimeoutException:
            await self.log(
                "[DEBUG TRACE] Slideshow wrapper not found\n",
                ctx
            )
            return []

        def get_slide_urls():
            return driver.execute_script("""
                const wrapper = document.querySelector(".swiper-wrapper");

                if (!wrapper) return [];

                const urls = [];

                for (const slide of wrapper.children) {
                    for (const img of slide.querySelectorAll("img")) {
                        const url = img.currentSrc || img.src;

                        if (
                            url &&
                            url.startsWith("https://") &&
                            !urls.includes(url)
                        ) {
                            urls.push(url);
                        }
                    }
                }

                return urls;
            """)

        image_urls = get_slide_urls()

        # Navigate through slides, collecting images as they appear.
        previous_active_url = None

        for slide_number in range(35):
            try:
                active_url = driver.execute_script("""
                    const img = document.querySelector(
                        ".swiper-slide-active img"
                    );

                    return img ? (img.currentSrc || img.src) : null;
                """)

                if not active_url or active_url == previous_active_url:
                    break

                previous_active_url = active_url

                if active_url not in image_urls:
                    image_urls.append(active_url)

                next_buttons = driver.find_elements(
                    By.CSS_SELECTOR,
                    ".swiper-button-next, "
                    "button[aria-label*='Next'], "
                    "button[aria-label*='next']"
                )

                if not next_buttons:
                    break

                next_button = next_buttons[0]

                if (
                    "swiper-button-disabled" in
                    (next_button.get_attribute("class") or "")
                    or next_button.get_attribute("disabled") is not None
                ):
                    break

                next_button.click()

                WebDriverWait(
                    driver,
                    5,
                    0.25,
                    (StaleElementReferenceException,)
                ).until(
                    lambda d: d.execute_script("""
                        const img = document.querySelector(
                            ".swiper-slide-active img"
                        );

                        return img &&
                            (img.currentSrc || img.src) !== arguments[0];
                    """, previous_active_url)
                )

                for url in get_slide_urls():
                    if url not in image_urls:
                        image_urls.append(url)

            except TimeoutException:
                break

            except StaleElementReferenceException:
                continue

        await self.log(
            f"[DEBUG TRACE] Slideshow extraction complete: "
            f"{len(image_urls)} images\n",
            ctx
        )

        return image_urls

    
    async def web_scrape(self, driver, ctx, headers, spoilerwarning, *, userinput=None, override=False):
            await self.log(f'[DEBUG TRACE] Jarvis, initiate TikTok protocol\n', ctx)

            link = await self.run_prechecks(driver, ctx, spoilerwarning, userinput=userinput, override=override)
            if link is None: return
        
            media = await self.find_video(driver, ctx)

            all_cookies = driver.get_cookies()
            cookies = {cookies['name']:cookies['value'] for cookies in all_cookies}

            if media is None:
                await self.log("[DEBUG TRACE] No playable video found. Switching to DOM slideshow extraction\n",ctx)

                image_urls = await self.find_slideshow_images(driver, ctx)

                if not image_urls:
                    await self.log("[DEBUG TRACE] No slideshow images found in DOM\n",ctx)
                    raise ValueError("No slideshow images could be extracted")

                await self.log(f'[DEBUG TRACE] closing session\n', ctx)
                driver.quit()
                driver = None

                await self.process_slideshow(ctx,headers,spoilerwarning,image_urls=image_urls,cookies=cookies,userinput=link)

                return


            if media["type"] == "video":
                # Minimal comparison diagnostics.
                video_diagnostics = driver.execute_script("""
                    const images = Array.from(document.images);

                    return {
                        url: location.href,
                        readyState: document.readyState,
                        videoCount: document.querySelectorAll("video").length,
                        imageCount: images.length,
                        loadedImages: images.filter(
                            img => img.complete && img.naturalWidth > 0
                        ).length,
                        universalData: !!document.getElementById(
                            "__UNIVERSAL_DATA_FOR_REHYDRATION__"
                        )
                    };
                """)

                await self.log(
                    "[DEBUG TRACE] Video post DOM:\n"
                    + json.dumps(video_diagnostics, indent=2)
                    + "\n",
                    ctx
                )


                await self.log(f'[DEBUG TRACE] closing session\n', ctx)
                driver.quit()
                driver =None

                url = media["url"]

                if os.path.exists('output.mp4'):
                    os.remove('output.mp4')
                    await self.log('[DEBUG TRACE] file removed\n', ctx)

                MAX_VIDEO_SIZE = 20 * 1024 * 1024  # 20 MB

                with requests.get(
                    url,
                    cookies=cookies,
                    headers=headers,
                    stream=True,
                    timeout=(10, 30)
                ) as r:
                    r.raise_for_status()

                    content_length = r.headers.get("Content-Length")

                    if content_length and int(content_length) > MAX_VIDEO_SIZE:
                        await self.handle_large_upload(ctx, url, link, spoilerwarning=spoilerwarning)
                        return

                    downloaded = 0
        
                    with open('output.mp4', 'wb') as f:
                        for chunk in r.iter_content(chunk_size=64 * 1024):
                            if not chunk:
                                continue

                            downloaded += len(chunk)

                            if downloaded > MAX_VIDEO_SIZE:
                                f.close()
                                os.remove('output.mp4')

                                await self.handle_large_upload(ctx, url, link, spoilerwarning=spoilerwarning)
                                return

                            f.write(chunk)
                    await self.log('[DEBUG TRACE] video downloaded\n', ctx)

                log_file_content = validate_file()
                
                await self.log(f'[DEBUG TRACE] ffmpeg error log: {log_file_content}', ctx)

                try:
                    await self.generic_output(ctx, link=link, spoilerwarning=spoilerwarning)
                    await self.log('[DEBUG TRACE] file sent\n', ctx)
                    self.lastlink = link
                except discord.HTTPException as e:
                    if e.code == 40005:
                        await self.log('[DEBUG TRACE] file upload failed. Initiating large upload sequence\n', ctx)
                        await self.handle_large_upload(ctx, url, link, spoilerwarning=spoilerwarning)
                    else:
                        raise
                
    
    async def process_slideshow(self, ctx, headers, spoilerwarning, *, image_urls, cookies, userinput=None):
                await self.log(f'[DEBUG TRACE] Jarvis, initiate TikTok Photos protocol\n', ctx)

                if not image_urls:
                    raise ValueError("No slideshow image URLs provided")    
                
                await self.log(f"[DEBUG TRACE] Downloading {len(image_urls)} slideshow images\n",ctx)

                files = []
                temp_paths = []

                async def send_batch():
                    nonlocal files, temp_paths

                    if not files:
                        return

                    try:
                        await ctx.channel.send(files=files)

                        await self.log(f"[DEBUG TRACE] Sent batch of {len(files)} photos\n",ctx)

                    finally:
                        for file in files:
                            file.close()

                        for path in temp_paths:
                            try:
                                if os.path.exists(path):
                                    os.remove(path)
                            except OSError as e:
                                await self.log(f"[DEBUG TRACE] Failed to remove temporary image {path}: {e}\n",ctx)

                        files.clear()
                        temp_paths.clear()
                        await self.log('[DEBUG TRACE] files cleared\n', ctx)

                for index, url in enumerate(image_urls, start=1):
                    await self.log(f"[DEBUG TRACE] Downloading photo {index}/{len(image_urls)}\n",ctx)

                    with requests.get(
                        url,
                        cookies=cookies,
                        headers=headers,
                        stream=True,
                        timeout=(10, 30)
                    ) as r:
                        r.raise_for_status()

                        content_type = r.headers.get(
                            "Content-Type", ""
                        ).split(";")[0].lower()

                        extensions = {
                            "image/jpeg": ".jpg",
                            "image/png": ".png",
                            "image/webp": ".webp",
                            "image/gif": ".gif"
                        }

                        extension = extensions.get(content_type, ".jpg")

                        # Create a temporary file for this slide.
                        fd, filename = tempfile.mkstemp(
                            prefix="tiktok_slide_",
                            suffix=extension
                        )
                        os.close(fd)

                        try:
                            with open(filename, "wb") as output:
                                for chunk in r.iter_content(
                                    chunk_size=64 * 1024
                                ):
                                    if chunk:
                                        output.write(chunk)

                            if os.path.getsize(filename) == 0:
                                raise ValueError(f"Downloaded image {index} is empty")

                            files.append(discord.File(filename,spoiler=spoilerwarning))

                            temp_paths.append(filename)

                            await self.log(f"[DEBUG TRACE] Photo {index} downloaded\n",ctx)

                        except Exception:
                            if os.path.exists(filename):
                                os.remove(filename)
                            raise

                    if len(files) == 9:
                        await send_batch()

                # Send remaining images.
                await send_batch()

                await self.log('[DEBUG TRACE] photos sent\n',ctx)

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

        if '.tiktok.com/' not in message.content and '.tt.site/' not in message.content and '.instagram.com/' not in message.content:
            return

        if message.content.startswith("||") and message.content.endswith("||"):
            spoilerwarning = True

        service = Service(executable_path=CHROME_DRIVER_PATH)

        async with self.scrape_lock:

            driver = create_driver(headers, block_images=True)

            try:
                if ('.tiktok.com/' in message.content or '.tt.site/' in message.content) and '/@' not in message.content:
                    await self.web_scrape(driver, message, headers, spoilerwarning)
                if '.instagram.com/' in message.content:
                    await self.process_ig(driver, message, headers, spoilerwarning)
            except Exception as e: 
                if '.instagram.com/' in message.content:
                    # suppress error (experimental feature)
                    return
                await self.log(f'[DEBUG TRACE] Standard error detected: {e}\n', message)
                await self.handle_error(e, message)
            finally:
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception as e:
                        await self.log(f'[DEBUG TRACE] Error closing session: {e}\n', message)
