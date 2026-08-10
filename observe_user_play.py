import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def main():
    print("==================================================")
    print("MANUAL PLAY OBSERVER — SCREENSHOTS EVERY 5 SECONDS FOR 2 MINUTES")
    print("==================================================")

    out_dir = os.path.join(os.path.dirname(__file__), "manual_edge_case_snapshots")
    os.makedirs(out_dir, exist_ok=True)

    # Clean old snapshots
    for f in os.listdir(out_dir):
        if f.endswith(".png"):
            try:
                os.remove(os.path.join(out_dir, f))
            except Exception:
                pass

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--window-size=1280,720")
    # Store profile in temp folder to avoid singleton lock issues
    profile_dir = os.path.join(os.path.dirname(__file__), "chrome_profiles", "manual_observer")
    os.makedirs(profile_dir, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")

    os.environ['WDM_SSL_VERIFY'] = '0'
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get("http://127.0.0.1:8080")
        time.sleep(2)
        
        # Unpause Scratch runtime so user can play manually with real mouse
        driver.execute_script("window.isResetting = true; if (window.resetGame) window.resetGame();")
        
        print("\n🌐 Chrome window open and unpaused!")
        print("🎮 PLAY FREELY IN THE CHROME WINDOW NOW!")
        print("Taking screenshots every 5 seconds for 120 seconds (24 snapshots total)...\n")
        
        start_time = time.time()
        for count in range(1, 25):
            time.sleep(5.0)
            elapsed = time.time() - start_time
            img_path = os.path.join(out_dir, f"snap_{count:02d}_{int(elapsed)}s.png")
            driver.save_screenshot(img_path)
            
            # Fetch current telemetry from browser window
            py = driver.execute_script("return window.getStageVar ? window.getStageVar('PLAYER Y') : 'N/A'")
            px = driver.execute_script("return window.getStageVar ? window.getStageVar('PLAYER X') : 'N/A'")
            frame = driver.execute_script("return window.getStageVar ? window.getStageVar('FRAME') : 'N/A'")
            
            print(f"[{count:02d}/24 | {elapsed:4.1f}s] Screenshot saved: snap_{count:02d}_{int(elapsed)}s.png | Pos: ({px}, {py}) | Frame: {frame}")

        print("\n✅ 2-minute manual play observation complete!")
    except Exception as e:
        print(f"Error during observation: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
