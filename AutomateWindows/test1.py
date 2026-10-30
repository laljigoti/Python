import time
import pyautogui
import pygetwindow as gw

def coordinate_finder():
    print("Find your window title (e.g., 'TeamViewer')...")
    windows = gw.getWindowsWithTitle('TeamViewer') # Change to your window title if needed
    
    if not windows:
        print("Window not found!")
        return
    
    win = windows[0]
    print(f"Tracking mouse relative to window: {win.title}")
    print("Move your mouse over the button and note the relative X/Y ratios or pixels. Press Ctrl+C to stop.\n")
    
    try:
        while True:
            # Get current mouse position
            mouse_x, mouse_y = pyautogui.position()
            
            # Calculate position relative to the window's top-left corner
            rel_x = mouse_x - win.left
            rel_y = mouse_y - win.top
            
            # Calculate percentages (useful if window size changes)
            pct_x = rel_x / win.width if win.width > 0 else 0
            pct_y = rel_y / win.height if win.height > 0 else 0
            
            print(f"Relative Pixels: X={rel_x}, Y={rel_y} | Percentages: X={pct_x:.2f}, Y={pct_y:.2f}", end="\r")
            print(f"Absolute Screen Coordinates: X={mouse_x}, Y={mouse_y}", end="\r")
            time.sleep(0.1)

            
    except KeyboardInterrupt:
        print("\nExiting coordinate finder.")

if __name__ == "__main__":
    coordinate_finder()