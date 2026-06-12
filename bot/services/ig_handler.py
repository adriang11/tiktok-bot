
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

    await client.breakpoint("IG Snapshot 1:", driver, ctx)
    
    try:
        wrapper = WebDriverWait(driver, 10, 0.5, (StaleElementReferenceException)).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="presentation"]')))
        await client.log(f'[DEBUG TRACE] outer wrapper found\n', ctx)

        inner_wrapper = WebDriverWait(wrapper, 10, 0.5, (StaleElementReferenceException)).until(EC.presence_of_element_located((By.TAG_NAME, 'div')))
        await client.log(f'[DEBUG TRACE] inner wrapper found\n', ctx)

        divs = WebDriverWait(inner_wrapper, 10, 0.5, (StaleElementReferenceException)).until(lambda x: x.find_elements(By.TAG_NAME, 'li'))
        await client.log(f'[DEBUG TRACE] li found\n', ctx)
        
        await client.breakpoint("IG Snapshot 2:", driver, ctx)

        files = []
        found = []
        fnum = 0
        for i in divs:
            imgs = i.find_elements(By.TAG_NAME, 'img')
            if not imgs: continue

            container = imgs[0]
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
                await client.log('[DEBUG TRACE] files cleared\n', ctx)
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
        await client.log('[DEBUG TRACE] files cleared\n', ctx)
        fnum = 0
    except TimeoutException as e:
        # 1 photo only

        div = driver.find_element(By.CLASS_NAME, '_aagv')
        imgs = div.find_elements(By.TAG_NAME, 'img')

        container = imgs[0]
        url = container.get_attribute('src')
        all_cookies = driver.get_cookies()
        cookies = {cookies['name']:cookies['value'] for cookies in all_cookies}

        r = requests.get(url, cookies=cookies, headers=headers, stream=True)

        filename = f"img1.png"
        with open(filename, 'wb') as out_file:
            shutil.copyfileobj(r.raw, out_file)
        del r

        await ctx.channel.send(file=discord.File(filename, spoiler=spoilerwarning))

        os.remove(f'img1.png')

        await client.log('[DEBUG TRACE] files cleared\n', ctx)