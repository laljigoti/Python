import time
import psutil

def wait_for_system_boot(min_uptime_seconds=30):
    print("Checking system startup status...")
    while True:
        # Get system uptime in seconds
        uptime = time.time() - psutil.boot_time()
        
        if uptime >= min_uptime_seconds:
            print(f"System is up and stable (Uptime: {int(uptime)} seconds).")
            break
        else:
            print(f"Windows just started. Waiting for stabilization... ({int(uptime)}/{min_uptime_seconds}s)", end="\r")
            time.sleep(2)

if __name__ == "__main__":
    wait_for_system_boot(30) # Waits until PC has been on for at least 30 seconds