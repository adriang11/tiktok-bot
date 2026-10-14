from selenium import webdriver

def create_driver(headers):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')     
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-gpu")
        options.add_argument('--no-sandbox')

        # Disable unnecessary features to improve performance
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--no-first-run")
        options.add_argument("--window-size=1920,1080")

        options.add_argument(f"user-agent={headers['User-Agent']}")

        return webdriver.Chrome(options=options) # CHROMEDRIVER_PATH is no longer needed