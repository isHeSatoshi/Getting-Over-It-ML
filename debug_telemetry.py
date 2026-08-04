import subprocess
import time
import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

PORT = 8000
GAME_DIR = "Getting Over It v1"

def test_telemetry():
    print(f"🚀 Starting Game Server on port {PORT}...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT)],
        cwd=os.path.join(os.getcwd(), GAME_DIR),
        # Remove DEVNULL to see if there are errors starting the server
    )
    
    time.sleep(2)
    
    try:
        print("🔍 Launching Selenium for log inspection...")
        options = Options()
        options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        # options.add_argument("--headless") # Uncomment if you don't want a window
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(f"http://localhost:{PORT}")
        
        print("⏳ Waiting 10 seconds for logs to appear...")
        for i in range(20):
            logs = driver.get_log('browser')
            for entry in logs:
                print(f"LOG: {entry['message']}")
            time.sleep(0.5)
            
        print("Done.")
        
    finally:
        print("🧹 Cleaning up...")
        if 'driver' in locals():
            driver.quit()
        server_process.terminate()

if __name__ == "__main__":
    test_telemetry()
