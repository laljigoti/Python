import time
from pynput import mouse

def on_click(x, y, button, pressed):
    if pressed:
        coord_str = f"Absolute Screen X: {x}, Y: {y}\n"
        print(f"Saved Click Position -> {coord_str.strip()}")
        
        # Write the absolute coordinates to a text file
        with open("coordinates.txt", "a") as f:
            f.write(coord_str)
        print("Coordinates appended to 'coordinates.txt'.\n")

def main():
    print("=== Console Coordinate Logger ===")
    print("Click anywhere on the screen. The coordinates will be shown here and saved to 'coordinates.txt'.")
    print("Press Ctrl+C in the console to exit.\n")
    
    # Start the mouse listener in a blocking call (keeps console open and interactive)
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()

if __name__ == "__main__":
    main()