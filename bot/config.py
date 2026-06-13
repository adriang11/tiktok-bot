import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TOKEN')
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')
WISDOM = os.getenv('ENCODED_FILE')
DIVS_WISDOM = os.getenv('DIVS_ENCODED_FILE')
TINYURL_KEY = os.getenv('TINYURL_KEY')
SHORTIO_KEY = os.getenv('SHORTIO_KEY')