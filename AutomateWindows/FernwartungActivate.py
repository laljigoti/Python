import time
import json
import os
import subprocess
import pyautogui
import pygetwindow as gw
import psutil

def load_config():
    config_path = "config.json"
    if not os.path.exists(config_path):
        default_config = {
            "Application": "Serviceportal",
            "app_path": "C:\\Path\\To\\Your\\serviceportal.exe",
            "target_x": 993,
            "target_y": 56,
            "target_x1": 1058,
            "target_y1": 602,
            "uptime_threshold": 120
        }
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        print(f"Created default '{config_path}' file. Please make sure to configure your 'app_path'.")
        return default_config
    
    with open(config_path, "r") as f:
        return json.load(f)

def activate_and_click():
    # Load coordinates, app name, and app path from external config file
    config = load_config()
    Application = config.get("Application", "Serviceportal")
    app_path = config.get("app_path", "")
    target_x = config.get("target_x", 993)
    target_y = config.get("target_y", 56)
    target_x1 = config.get("target_x1", 1058)
    target_y1 = config.get("target_y1", 602)
    
    print(f"Searching for window titled '{Application}'...")
    windows = gw.getWindowsWithTitle(Application)
    
    # If window is missing, launch it via path from config.json
    if not windows:
        print(f"Window titled '{Application}' not found.")
        if app_path and os.path.exists(app_path):
            print(f"Launching application from path: {app_path}")
            try:
                subprocess.Popen(app_path)
            except Exception as e:
                print(f"Failed to launch application executable: {e}")
                return False
        else:
            print(f"Error: Application path '{app_path}' is invalid or missing in 'config.json'.")
            return False
        
        # Wait until the window appears and is running/stable
        print("Waiting for the application window to open and stabilize...")
        timeout = 60  # Max wait time in seconds
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            windows = gw.getWindowsWithTitle(Application)
            if windows:
                print(f"Application window '{Application}' detected and running!")
                time.sleep(2)  # Extra buffer for stable rendering
                break
            time.sleep(2)
        else:
            print(f"Timeout: Application window did not appear within {timeout} seconds.")
            return False
    
    win = windows[0]
    
    if win.isMinimized:
        win.restore()
        time.sleep(1)
    
    # Bypass Windows focus restriction (Error 5) by simulating a click 
    # on the window's title bar or area to bring it to the foreground safely
    try:
        win.activate()
        print(f"Window titled '{Application}' activated successfully.")
    except Exception as e:
        print(f"Direct activation blocked by Windows security. Using click fallback...")
        # Fallback: Click near the top of the window frame to focus it safely
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
        
        print(f"System is up and stable (Uptime: {int(uptime)} seconds).", end="\r")
        if uptime > int(uptime_threshold):  
            print("\nUptime threshold reached. Checking application state...")
            success = activate_and_click()
            if success:
                break  # Exit loop after successful execution
        
        time.sleep(1)