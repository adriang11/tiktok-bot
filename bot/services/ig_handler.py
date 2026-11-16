
import os
import discord
import shutil
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException


async def handle_ig_link(client, driver, ctx, headers, spoilerwarning):
    await client.log(f'[DEBUG TRACE] Jarvis, initiate Instagram Photos protocol\n', ctx)

    def get_ig_post_metadata(driver):
        username = None
        caption = None

        try:
            # Find username
            username_span = driver.find_element(By.CSS_SELECTOR, 'span._ap3a')

            username_link = username_span.find_element(By.XPATH, './ancestor::a[1]')

            username = (username_link.get_attribute('href').rstrip('/').split('/')[-1])

            caption_element = driver.find_element(By.CSS_SELECTOR, 'span.x126k92a')

            caption = caption_element.text.strip()

        except:
            pass

        return username, caption
    
    link = ctx.content
    
    # strip link from message if appicable
    lst = link.split(' ')
    for word in lst:
        if '.instagram.com/' in word:
            if word.startswith("||") and word.endswith("||"): spoilerwarning = True #foolproofing
            link = word.strip('||')

    await client.log(f'[DEBUG TRACE] extracted link: {link}\n', ctx)
    
    if '/reel/' in link: return

    driver.get(link)

    await client.log(f'[DEBUG TRACE] enter link\n', ctx)

    username, caption = get_ig_post_metadata(driver)

    await client.log(f'[DEBUG TRACE] IG username: {username}, caption length: {len(caption) if caption else 0}\n',ctx)

    # Format the Discord message
    ig_message = None

    if username:
        caption = ' '.join(caption.split()) if caption else ''

        if len(caption) > 100:
            caption = caption[:100].rstrip() + '... [Read more on IG]'

        ig_message = (f'@{username}: ' if username else '') + caption
        

    try:
        # Count the carousel indicators to determine the total number of slides
        indicators = WebDriverWait(driver, 5, 0.5, (StaleElementReferenceException)).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, '._acvz > ._acnb')
        )
        slide_count = len(indicators)
        await client.log(f'[DEBUG TRACE] {slide_count} slides found\n', ctx)

        # Remove existing query parameters so we can request each slide by index
        post_url = driver.current_url.split('?')[0]

        files = []
        fnum = 0

        # Visit each slide individually using img_index
        for i in range(1, slide_count + 1):
            driver.get(f'{post_url}?img_index={i}')
            await client.log(f'[DEBUG TRACE] loading slide {i}/{slide_count}\n', ctx)

            # Find the carousel images for the requested slide
            wrapper = WebDriverWait(driver, 10, 0.5, (StaleElementReferenceException)).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="presentation"]'))
            )

            divs = WebDriverWait(wrapper, 10, 0.5, (StaleElementReferenceException)).until(
                lambda x: x.find_elements(By.TAG_NAME, 'li')
            )

            imgs = []
            for div in divs:
                imgs.extend(div.find_elements(By.TAG_NAME, 'img'))

            if not imgs:
                await client.log(f'[DEBUG TRACE] no images found for slide {i}\n', ctx)
                continue

            # Instagram renders the current slide and the next slide.
            # For index 1, use the first image; for later indices, use the second.
            image_position = 0 if i == 1 else 1

            if len(imgs) <= image_position:
                await client.log(
                    f'[DEBUG TRACE] expected image position {image_position} '
                    f'not found for slide {i}\n',
                    ctx
                )
                continue

            url = imgs[image_position].get_attribute('src')

            await client.log(
                f'[DEBUG TRACE] downloading slide {i} from image position '
                f'{image_position}\n',
                ctx
            )

            all_cookies = driver.get_cookies()
            cookies = {cookie['name']: cookie['value'] for cookie in all_cookies}

            r = requests.get(url, cookies=cookies, headers=headers, stream=True)
            r.raise_for_status()

            # Send files in batches of 9 to stay within Discord's attachment limit
            if len(files) == 9:
                await ctx.channel.send(files=files)

                num = 1
                for file in files:
                    os.remove(f'img{num}.png')
                    num += 1

                files.clear()
                await client.log('[DEBUG TRACE] files cleared\n', ctx)
                fnum = 0

            filename = f"img{fnum + 1}.png"
            with open(filename, 'wb') as out_file:
                fnum += 1
                shutil.copyfileobj(r.raw, out_file)
                files.append(discord.File(filename, spoiler=spoilerwarning))

            r.close()

        # Send any remaining files
        if files:
            await ctx.channel.send(files=files)

            num = 1
            for file in files:
                os.remove(f'img{num}.png')
                num += 1

            files.clear()
            await client.log('[DEBUG TRACE] files cleared\n', ctx)
            fnum = 0

        if ig_message:
            await ctx.channel.send(ig_message)

    except TimeoutException as e:
            # No carousel indicators found: assume this is a single photo
            await client.log('[DEBUG TRACE] no carousel found; trying single photo\n', ctx)

            div = driver.find_element(By.CLASS_NAME, '_aagv')
            imgs = div.find_elements(By.TAG_NAME, 'img')

            container = imgs[0]
            url = container.get_attribute('src')

            all_cookies = driver.get_cookies()
            cookies = {cookie['name']: cookie['value'] for cookie in all_cookies}

            r = requests.get(url, cookies=cookies, headers=headers, stream=True)
            r.raise_for_status()

            filename = 'img1.png'
            with open(filename, 'wb') as out_file:
                shutil.copyfileobj(r.raw, out_file)

            r.close()

            await ctx.reply(file=discord.File(filename, spoiler=spoilerwarning))

            if ig_message:
                await ctx.channel.send(ig_message)

            os.remove(filename)
            await client.log('[DEBUG TRACE] files cleared\n', ctx)