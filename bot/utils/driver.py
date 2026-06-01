from selenium import webdriver

def create_driver(headers):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-gpu")
        options.add_argument('--no-sandbox')
        options.add_argument(f"user-agent={headers}")

        return webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed