from selenium import webdriver

def create_driver(headers, *, block_images=False):
        options = webdriver.ChromeOptions()

        options.add_argument("--headless=new")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--no-first-run")
        options.add_argument("--window-size=800,600")

        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")

        options.page_load_strategy = "eager"

        if block_images:
                prefs = {
                "profile.managed_default_content_settings.images": 2
                }
                options.add_experimental_option("prefs", prefs)

        options.add_argument(f"user-agent={headers['User-Agent']}")

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(25)
        return driver