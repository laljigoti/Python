import os
import subprocess
import time

WORK_MIN = 1
SHORT_BREAK_MIN = 1
BAR_LENGTH = 30


def clear_screen():
    subprocess.run("cls" if os.name == "nt" else "clear", shell=True)


def format_time(seconds):
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


def draw_bar(remaining_seconds, total_seconds):
    fraction_done = 1 - (remaining_seconds / total_seconds)
    filled_length = int(BAR_LENGTH * fraction_done)
    bar = "#" * filled_length + "-" * (BAR_LENGTH - filled_length)
    return f"[{bar}]"


def run_phase(phase_name, duration_minutes):
    total_seconds = duration_minutes * 60
    remaining_seconds = total_seconds

    while remaining_seconds >= 0:
        clear_screen()
        print("=" * 40)
        print(f"{phase_name.upper()}")
        print("=" * 40)
        print()
        print(f"Time left: {format_time(remaining_seconds)}")
        print(f"Progress:  {draw_bar(remaining_seconds, total_seconds)}")
        print()
        print("Press Ctrl+C to stop")

        if remaining_seconds == 0:
            break

        time.sleep(1)
        remaining_seconds -= 1


def main():
    try:
        while True:
            run_phase("Work Time", WORK_MIN)
            print("\nWork session done! Starting break...\n")
            time.sleep(2)

            run_phase("Break Time", SHORT_BREAK_MIN)
            print("\nBreak's over! Back to work...\n")
            time.sleep(2)
    except KeyboardInterrupt:
        clear_screen()
        print("Pomodoro timer stopped. See you next session!")


if __name__ == "__main__":
    main()