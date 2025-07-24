import subprocess
import sys
import os
import time
import signal
import atexit

processes = []

def cleanup_processes():
    for process in processes:
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

def signal_handler(signum, frame):
    cleanup_processes()
    sys.exit(0)

def start_api_server():
    api_path = os.path.join(os.path.dirname(__file__), 'core-lumiere-api', 'server.py')
    process = subprocess.Popen([sys.executable, api_path])
    processes.append(process)
    return process

def start_discord_bot():
    bot_path = os.path.join(os.path.dirname(__file__), 'core-lumiere', 'bot.py')
    process = subprocess.Popen([sys.executable, bot_path])
    processes.append(process)
    return process

def main():
    atexit.register(cleanup_processes)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    api_process = start_api_server()
    time.sleep(5)
    bot_process = start_discord_bot()
    
    try:
        while True:
            if api_process.poll() is not None:
                break
            if bot_process.poll() is not None:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        cleanup_processes()

if __name__ == "__main__":
    main()