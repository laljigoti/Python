import psutil
import time

def check_teamviewer_status():
    target_name = "command-line ssh"  # Must be lowercase since we convert proc_name to lowercase
    found = False
    
    print("Scanning system processes for TeamViewer...")
    
    for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_info']):
        try:
            proc_name = proc.info['name'].lower()
            
            # Check if 'teamviewer' is in the process executable name
            if target_name in proc_name:
                found = True
                print(f"\n[Found Process]")
                print(f"  - PID: {proc.info['pid']}")
                print(f"  - Name: {proc.info['name']}")
                print(f"  - Status: {proc.info['status']}")
                print(f"  - CPU Usage: {proc.cpu_percent(interval=0.1)}%")
                print(f"  - Memory Usage: {proc.info['memory_info'].rss / (1024 * 1024):.2f} MB")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    if not found:
        print("TeamViewer process is currently NOT running.")

if __name__ == "__main__":
    check_teamviewer_status()