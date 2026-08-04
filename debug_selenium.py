from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

def test():
    print("Testing Selenium initialization...")
    chrome_options = Options()
    # Use standard options first
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        print("Driver created successfully.")
        driver.get("https://google.com")
        print(f"Title: {driver.title}")
        time.sleep(2)
        driver.quit()
        print("Driver quit successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
