import time
import pyautogui
import pygetwindow as gw

def activate_and_click():
    # 1. Find and activate the Serviceportal window from the taskbar/desktop
    windows = gw.getWindowsWithTitle('TeamViewer')
    
    if not windows:
        print("TeamViewer window not found. Make sure the application is open.")
        return
    
    win = windows[0]
    
    # Restore if minimized and bring to foreground
    if win.isMinimized:
        win.restore()
    win.activate()
    print("TeamViewer window activated.")
    
    # Wait a brief moment for the window to gain focus
    time.sleep(1)
    
    # 2. Locate and click the 'FERNWARTUNG ZULASSEN' button using image recognition
    button_image = 'fernwartung_btn.png'
    
    print("Searching for the 'FERNWARTUNG ZULASSEN' button...")
    try:
        # Locate center coordinates of the button on the screen
        location = pyautogui.locateCenterOnScreen(button_image, confidence=0.9)
        
        if location:
            pyautogui.click(location)
            print("Successfully clicked 'FERNWARTUNG ZULASSEN'.")
        else:
            print("Button not found on the screen. Check your template image.")
            
    except pyautogui.ImageNotFoundException:
        print("Could not find the button image on screen.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    activate_and_click()