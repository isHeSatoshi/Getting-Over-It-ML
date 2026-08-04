import time
import subprocess
import os
import sys
import math
import pyautogui
pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort
pyautogui.PAUSE = 0        # Remove built-in delay for maximum speed
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- PHYSICS CONSTANTS ---
HAMMER_LENGTH  = 100   # Scratch units — max radius the mouse is allowed from the pot
GROUND_Y       = -130  # Scratch Y below which hammer is considered "on ground"
VAULT_DRAG_PX  = 160   # Pixels to drag DOWN (positive = toward screen floor) for vault push
VAULT_DURATION = 0.06  # Seconds for vault drag — fast = more impulse
DEBUG          = True  # Set False to silence per-frame telemetry prints

# --- CONFIGURATION ---
PORT = 8000
GAME_DIR = "Getting Over It v1"

def start_local_server():
    """Launches the Python HTTP server as a background process."""
    print(f"🚀 Starting Game Server on port {PORT}...")
    return subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT)],
        cwd=os.path.join(os.getcwd(), GAME_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# Dynamically populated after Selenium calibration
CENT_X  = 320.0   # absolute screen X of the canvas center
CENT_Y  = 240.0   # absolute screen Y of the canvas center
STAGE_W = 640.0   # canvas width  in screen pixels
STAGE_H = 480.0   # canvas height in screen pixels

# Full monitor resolution — used for safe clamping
_SCREEN_W, _SCREEN_H = pyautogui.size()
BOUNDARY = 100  # px guardrail on all screen edges — prevents FailSafe corner triggers

def scratch_to_screen(sx, sy):
    """Maps Scratch coords to absolute screen pixels using the calibrated canvas center.

    Scratch X: -240 (left) to +240 (right)  → CENT_X is x=0
    Scratch Y: +180 (top)  to -180 (bottom) → CENT_Y is y=0, flipped (Scratch Y-up, Screen Y-down)
    Returns (tx, ty, boundary_hit).
    """
    tx = CENT_X + sx * (STAGE_W / 480)
    ty = CENT_Y - sy * (STAGE_H / 360)  # subtract: Scratch +Y = screen up = lower pixel value

    lo_x, hi_x = BOUNDARY, _SCREEN_W - BOUNDARY
    lo_y, hi_y = BOUNDARY, _SCREEN_H - BOUNDARY

    hit = tx < lo_x or tx > hi_x or ty < lo_y or ty > hi_y
    tx = max(lo_x, min(hi_x, tx))
    ty = max(lo_y, min(hi_y, ty))
    return tx, ty, hit


def get_vector(px, py, hx, hy):
    """Returns (distance, angle_deg) from pot (px,py) to hammer (hx,hy) in Scratch coords."""
    dx = hx - px
    dy = hy - py
    distance  = math.hypot(dx, dy)
    angle_deg = math.degrees(math.atan2(dy, dx))  # 0° = right, 90° = up (Scratch convention)
    return distance, angle_deg


def clamp_to_radius(px, py, hx, hy, max_len):
    """Clamp target (hx,hy) so it stays at most max_len Scratch units from pot (px,py)."""
    dist, angle = get_vector(px, py, hx, hy)
    if dist <= max_len:
        return hx, hy  # already inside radius — pass through unchanged
    rad = math.radians(angle)
    cx  = px + max_len * math.cos(rad)
    cy  = py + max_len * math.sin(rad)
    return cx, cy


def execute_vault(tx, ty):
    """Fast downward drag to vault the cat off the ground.

    VAULT_DRAG_PX is positive to move toward the screen floor (+Y in browser coords).
    scratch_to_screen already handles the Y-flip, so we simply ADD pixels here.
    """
    drag_target_y = min(_SCREEN_H - BOUNDARY, ty + VAULT_DRAG_PX)
    pyautogui.moveTo(tx, ty, _pause=False)
    pyautogui.dragTo(tx, drag_target_y, duration=VAULT_DURATION, button='left', _pause=False)
    print("🚀 VAULT!")


def main():
    server_process = None
    try:
        # 1. Boot the server
        server_process = start_local_server()
        time.sleep(2)

        # 2. Setup Selenium with Logging
        print("🔍 Launching AI Vision (Selenium)...")
        chrome_options = Options()
        chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.maximize_window()
        driver.get(f"http://localhost:{PORT}")

        # --- Auto-calibrate canvas center ---
        # getBoundingClientRect() → viewport-relative canvas position
        # get_window_rect()       → browser window's absolute screen position
        print("🎯 Calibrating stage position...")
        global CENT_X, CENT_Y, STAGE_W, STAGE_H
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By

            canvas = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#app canvas"))
            )
            rect = driver.execute_script("return arguments[0].getBoundingClientRect();", canvas)
            win  = driver.get_window_rect()

            STAGE_W = float(rect['width'])
            STAGE_H = float(rect['height'])
            CENT_X  = win['x'] + rect['left'] + STAGE_W / 2
            CENT_Y  = win['y'] + rect['top']  + STAGE_H / 2

            print(f"   Window origin : ({win['x']}, {win['y']})")
            print(f"   Canvas rect   : left={rect['left']:.0f}  top={rect['top']:.0f}  {STAGE_W:.0f}x{STAGE_H:.0f} px")
            print(f"   ✅ Stage center: ({CENT_X:.0f}, {CENT_Y:.0f}) on screen")
        except Exception as cal_err:
            print(f"   ⚠️  Calibration failed ({cal_err}), using fallback center ({CENT_X:.0f}, {CENT_Y:.0f})")
        # ------------------------------------

        # Hold mouse button down — the cat grips with a held click
        pyautogui.mouseDown(button='left')
        print("🖱️  Mouse held down — cat should grip.")

        print("⚡ Brain Active. Listening for STATE telemetry...")

        last_print_time = 0
        while True:
            logs = driver.get_log('browser')
            for entry in logs:
                msg = entry['message']

                if "STATE" in msg:
                    current_time = time.time()
                    should_print = DEBUG and (current_time - last_print_time >= 5.0)

                    if should_print:
                        print(f"📡 {msg}")
                    try:
                        # Expected format: STATE|P:x,y|H:x,y|A:y|D:deg
                        parts = msg.split('|')
                        p_val = parts[1].split(':')[1].split(',')
                        h_val = parts[2].split(':')[1].split(',')

                        px, py = float(p_val[0]), float(p_val[1])
                        hx, hy = float(h_val[0]), float(h_val[1])

                        # 1. Vector diagnostics
                        dist, angle = get_vector(px, py, hx, hy)
                        if should_print:
                            print(f"   ↗ dist={dist:.1f}  angle={angle:.1f}°")
                            last_print_time = current_time

                        # 2. Circular limiter — keep mouse within hammer reach of cat
                        cx, cy = clamp_to_radius(px, py, hx, hy, HAMMER_LENGTH)

                        # 3. Convert Scratch coords to screen pixels
                        tx, ty, boundary_hit = scratch_to_screen(cx, cy)
                        if boundary_hit:
                            raw_tx = CENT_X + cx * (STAGE_W / 480)
                            raw_ty = CENT_Y - cy * (STAGE_H / 360)
                            print(f"⚠️  WARNING: Boundary Hit! raw=({raw_tx:.0f},{raw_ty:.0f}) clamped to ({tx:.0f},{ty:.0f})")

                        # 4. Vault detection — hammer near/on ground
                        if hy < GROUND_Y:
                            execute_vault(tx, ty)
                        else:
                            # CIRCULAR TEST DRIVE: orbits around the pot to create swing
                            # Uncomment the line below and remove the circle block to switch to Magnet Mode
                            # pyautogui.moveTo(tx, ty, _pause=False)
                            circle_angle  = (time.time() * 2) % (2 * math.pi)  # one revolution ~3.14s
                            circle_radius = 80  # Scratch units — well within HAMMER_LENGTH

                            target_sx = px + circle_radius * math.cos(circle_angle)
                            target_sy = py + circle_radius * math.sin(circle_angle)
                            tx, ty, _ = scratch_to_screen(target_sx, target_sy)
                            pyautogui.moveTo(tx, ty, _pause=False)

                    except (IndexError, ValueError) as e:
                        print(f"Telemetry Parse Error: {e}")

            time.sleep(0.01)  # ~100Hz polling rate

    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        if server_process:
            server_process.terminate()
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    main()