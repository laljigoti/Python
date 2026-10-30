import time
import json
import os
import pyautogui
import pygetwindow as gw

def load_config():
    config_path = "config.json"
    if not os.path.exists(config_path):
        default_config = {
            "target_x": 1021,
            "target_y": 138,
            "target_x1": 1036,
            "target_y1": 613
        }
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        print(f"Created default '{config_path}' file.")
        return default_config
    
    with open(config_path, "r") as f:
        return json.load(f)

def activate_and_click():
    config = load_config()
    target_x = config.get("target_x", 1021)
    target_y = config.get("target_y", 138)
    target_x1 = config.get("target_x1", 1036)
    target_y1 = config.get("target_y1", 613)

    app_title = 'TeamViewer'
    print(f"Searching for window: '{app_title}'...")
    
    windows = gw.getWindowsWithTitle(app_title)
    if not windows:
        print(f"Error: Window with title '{app_title}' not found. Exiting application.")
        return
    
    win = windows[0]
    
    if win.isMinimized:
        win.restore()
    
    win.activate()
    print("Activation requested. Verifying if window is successfully focused...")
    
    # Wait up to 5 seconds for the window to become active
    timeout = 5
    start_time = time.time()
    activated = False
    
    while time.time() - start_time < timeout:
        # Check active window title
        active_win = gw.getActiveWindow()
        if active_win and app_title.lower() in active_win.title.lower():
            activated = True
            break
        time.sleep(0.5)
    
    if not activated:
        print(f"Timeout: Could not verify that '{app_title}' is activated. Exiting application.")
        return
    
    print(f"'{app_title}' is successfully activated and in focus.")
    time.sleep(1)
    
    # Move the mouse cursor to the first position
    pyautogui.moveTo(target_x, target_y, duration=0.5)
    print(f"Moved mouse to screen coordinates X={target_x}, Y={target_y}. Waiting for 5 seconds...")
    
    time.sleep(5)
    
    # Click the first position
    pyautogui.click()
    time.sleep(1)
    
    # Move and click the second position
    pyautogui.moveTo(target_x1, target_y1, duration=0.5)
    pyautogui.click()
    print("Successfully completed actions.")

if __name__ == "__main__":
    activate_and_click()