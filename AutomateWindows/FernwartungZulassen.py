import time
import json
import os
import pyautogui
import pygetwindow as gw
import psutil


def load_config():
    config_path = "config.json"
    if not os.path.exists(config_path):
        default_config = {
            "Application": "TeamViewer",
            "target_x": 993,
            "target_y": 56,
            "target_x1": 1058,
            "target_y1": 602,
            "uptime_threshold": 120
        }
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        print(f"Created default '{config_path}' file.")
        return default_config
    
    with open(config_path, "r") as f:
        return json.load(f)

def activate_and_click():
    # Load coordinates and app name from external config file
    config = load_config()
    Application = config.get("Application", "TeamViewer")
    target_x = config.get("target_x", 993)
    target_y = config.get("target_y", 56)
    target_x1 = config.get("target_x1", 1058)
    target_y1 = config.get("target_y1", 602)

    print(f"Searching for window titled '{Application}'...")
    windows = gw.getWindowsWithTitle(Application)

    # Safe check if window is missing
    if not windows:
        print(f"Window titled '{Application}' not found. Waiting 20 seconds...")
        time.sleep(20)
        windows = gw.getWindowsWithTitle(Application)
        if not windows:
            print(f"Error: Window '{Application}' still not found. Exiting.")
            return False

    win = windows[0]

    # --- Minimize all other windows first ---
    print("Minimizing all windows...")
    for w in gw.getAllWindows():
        try:
            # Skip windows without a title and the target window itself
            #if w.title and w._hWnd != win._hWnd and not w.isMinimized:
                w.minimize()
        except Exception:
            # Some system windows can't be minimized, ignore them
            pass
    time.sleep(2)

    # --- Restore and activate the target application ---
    if win.isMinimized:
        win.restore()
        time.sleep(2)

    try:
        win.activate()
        print(f"Window titled '{Application}' activated successfully.")
    except Exception:
        print("Direct activation blocked by Windows security. Using click fallback...")
        pyautogui.click(win.left + 100, win.top + 10)

    time.sleep(1)

    # Move the mouse cursor to the first position
    pyautogui.moveTo(target_x, target_y, duration=0.5)
    print(f"Moved mouse to screen coordinates X={target_x}, Y={target_y}. Waiting for 3 seconds...")

    time.sleep(3)

    # Click the first position
    pyautogui.click()
    time.sleep(1)

    # Move and click the second position
    pyautogui.moveTo(target_x1, target_y1, duration=0.5)
    pyautogui.click()
    print("Successfully completed actions.")
    return True

if __name__ == "__main__":
    config = load_config()
    uptime_threshold = config.get("uptime_threshold", 120)
    print("Starting Fernwartung Zulassen script...")
    print(f"Waiting for uptime to exceed {uptime_threshold} seconds...")
    while True:
        uptime = time.time() - psutil.boot_time()
        
        
        
        # Change threshold as needed (e.g., 10 seconds for testing)
       
        print(f"System is up and stable (Uptime: {int(uptime)} seconds).", end="\r")
        if uptime > int(uptime_threshold):  
            print("\nUptime threshold reached. Executing automation...")
            success = activate_and_click()
            if success:
                break  # Exit loop after successful execution
        
        time.sleep(1)