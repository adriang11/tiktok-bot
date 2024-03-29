import os
import discord
import time
import traceback
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

load_dotenv()
TOKEN = os.getenv('TOKEN')
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'{client.user} is Ready to go!!')
        # await tree.sync(guild=discord.Object(id=Your guild id))
        await self.change_presence(activity=discord.Game(name="League of Legends"))
        dungeon = client.get_channel(1149980884523556915)
        ducklings = client.get_channel(915088526129909842)
        # await dungeon.send('I am alive and capable of feeling.')
        # await ducklings.send('I am alive and capable of feeling.')

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        
        if '.tiktok.com/' not in message.content:
            return

        service = Service(executable_path=CHROME_DRIVER_PATH)

        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')

        try:
            # initialize the Selenium WebDriver
            driver = webdriver.Chrome(service=service, options=options)

            driver.get(message.content)
            print(f'[DEBUG TRACE] tiktok link: {message.content}\n')

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
            print('oopsies\n')
            traceback.print_exc()
            await message.reply(content=('Error: ' + str(e)), mention_author=True)
        finally:
            driver.quit()
    
    # @tree.command(name = "commandname", description = "My first application Command", guild=discord.Object(id=12417128931)) #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
    # async def first_command(interaction):
    #     await interaction.response.send_message("Hello!")

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
# tree = app_commands.CommandTree(client)

client.run(TOKEN)


