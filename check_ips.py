'''
https://github.com/induna-crewneck/Public-IP-Checker
v3

Changelog:
- Removed timestamp from Telegram message (already provided in form of automatic message timestamp)
- Showing all IPs when notifying about change
- Notifying about docker container IP change only if it matches the regular public IP (this was done because VPN-based IPs change often)
- Cosmetic formatting of Log Output
To Do:
'''

import os
import time
import requests
import subprocess
import re
from datetime import datetime

# Load environment variables

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30)) * 60
DOCKER_CONTAINER = os.getenv("DOCKER_CONTAINER")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_RECEIVER = os.getenv("TELEGRAM_RECEIVER")
log_file = "/app/public-ips.log"
ips_file = "/app/public-ips.txt"

ipv4_regex = r"^\d*\.\d*\.\d*\.\d*$"
if len(DOCKER_CONTAINER) > 10:
    spacing_length = len(DOCKER_CONTAINER) + 3
else:
    spacing_length = 10

def log_message(message):
    with open(log_file, "a") as f:
        f.write(f"{message}\n")
    # Log to Docker logs
    print(message)

def get_ip_location(ip):
    if ip == "127.0.0.1":
        return "Inside the House 👻"
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        if response.status_code == 200:
            data = response.json()
            city = data.get("city", "Unknown City")
            region = data.get("region", "Unknown Region")
            country = data.get("country", "Unknown Country")
            location_string = f"{city}, {region}, {country}"
            return location_string
        else:
            log_message(f"Could not fetch location from ipinfo.io, {response.status_code}, {response.text}")
            return "N/A"
    except Exception as e:
        log_message(f"Exception while fetching location data: {e}")
        return "N/A"

def get_public_ip():
    try:
        public_ip = requests.get("https://api.ipify.org")
        if re.fullmatch(ipv4_regex, public_ip.text):
            return public_ip.text
        else:
            log_message(f"ipify did not return valid public IP: {public_ip}")
    except Exception as e:
        log_message(f"Exception getting public IP from ipify: {e}")
    try:
        public_ip = requests.get("https://ipv4.icanhazip.com")
        if re.fullmatch(ipv4_regex, public_ip.text.strip()):
            log_message(f"icanhazip fallback successful")
            return public_ip.text.strip()
        else:
            log_message(f"icanhazip did not return valid public IP: {public_ip}")
        return "failed"
    except Exception as e:
        log_message(f"Exception getting public IP from icanhazip: {e}")
        return "failed"

def get_local_ip():
    try:
        return subprocess.check_output(["hostname", "-I"]).decode().split()[0]
    except Exception as e:
        log_message(f"Failed to get local IP (1): {e}")
    try:
        return subprocess.check_output(["ipconfig", "getifaddr", "en0"]).decode().strip()
    except Exception as e:
        log_message(f"Failed to get local IP (2): {e}")
    try:
        return subprocess.check_output(["ipconfig", "getifaddr", "en1"]).decode().strip()
    except Exception as e:
        log_message(f"Failed to get local IP (3): {e}")
    try:
        return subprocess.check_output(["hostname"]).decode().split()[0]
    except Exception as e:
        log_message(f"Failed to get local IP (4): {e}")
    return "N/A"

def get_docker_ip(container_name):
    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "curl", "-s", "https://api.ipify.org"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            docker_ip = result.stdout.decode().strip()
            if re.match(ipv4_regex, docker_ip):
                return docker_ip
            else:
                log_message(f"ipify did not return valid {DOCKER_CONTAINER} IP: {docker_ip}")
        else:
            log_message(f"ipify did not return valid {DOCKER_CONTAINER} IP: {result.stderr.decode()}")
    except Exception as e:
        log_message(f"Exception getting {DOCKER_CONTAINER} IP from ipify: {e}")
    try:
        result_fallback = subprocess.run(
            ["docker", "exec", container_name, "curl", "-s", "https://ipv4.icanhazip.com"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result_fallback.returncode == 0:
            docker_ip = result_fallback.stdout.decode().strip()
            if re.match(ipv4_regex, docker_ip):
                return docker_ip
            else:
                log_message(f"icanhazip did not return valid {DOCKER_CONTAINER} IP: {docker_ip}")
    except Exception as e:
        log_message(f"Exception getting {DOCKER_CONTAINER} IP from icanhazip: {e}")
    return "failed"

def send_telegram_message(message):
    try:
        # message += f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_RECEIVER, "text": message}
        telegramresponse = requests.post(url, data=payload)
        if "200" not in str(telegramresponse): log_message(f"Telegram Response: {telegramresponse.text}")
    except Exception as e:
        log_message(f"Failed to send Telegram message: {e}")

def fetch_ips():
    try:
        current_ips = {
            "local": get_local_ip(),
            "public": get_public_ip(),
            f"{DOCKER_CONTAINER}": get_docker_ip(DOCKER_CONTAINER),
        }
        return current_ips
    except Exception as e:
        log_message(f"Failed to fetch IPs: {e}")
    return {"local": "", "public": "", "router": "", f"{DOCKER_CONTAINER}": ""}

def initial_messaging():
    initial_ips = fetch_ips()
    try:
        for key, value in initial_ips.items():
            if key == DOCKER_CONTAINER:
                # location = get_ip_location(value)
                log_message(f"{key} IP:{' ' * (spacing_length - len(key))}{value} ({get_ip_location(value)})")
            else:
                log_message(f"{key} IP:{' ' * (spacing_length - len(key))}{value}")
    except Exception as e:
        log_message(f"Failed to log initial IPs: {e}")
    try:
        with open(ips_file, "w") as f:
            for key, value in initial_ips.items():
                f.write(f"{key}: {value}\n")
    except Exception as e:
        log_message(f"Failed to write initial IPs: {e}")
    try:
        initial_message = "Watchdog started\n\n"
        for key, value in initial_ips.items():
            if key == DOCKER_CONTAINER:
                location = get_ip_location(value)
                initial_message += f"{key} IP: {value} ({location})\n"

                docker_initial = value
            else:
                initial_message += f"{key} IP: {value}\n"
                if key == "public":
                    public_initial = value
        if public_initial == docker_initial:
            initial_message += f"🚨 {DOCKER_CONTAINER} IP = Public IP 🚨"
        send_telegram_message(initial_message)
    except Exception as e:
        log_message(f"Failed to send initial Telegram message: {e}")

    return initial_ips

def main():

    print(f"{'='*64}\n{'='*23} Public IP Checker {'='*22}\n{'='*5} https://github.com/induna-crewneck/Public-IP-Checker {'='*5}\n{'='*64}", end="\n")
    global previous_ips
    previous_ips = {"local": "", "public": "", f"{DOCKER_CONTAINER}": ""}

    log_message("Starting IP Checker...")

    previous_ips = initial_messaging()

    if CHECK_INTERVAL > 0:
        log_message(f"Starting loop with CHECK_INTERVAL {CHECK_INTERVAL} seconds")
    else:
        log_message(f"CHECK_INTERVAL was set to 0. exiting")
        exit()

    loopcounter = 0

    while True:
        loopcounter += 1
        if loopcounter % 100 == 0:
            # loopcount is divisible by 100
            log_message(f"Loop #{loopcounter}")

        time.sleep(CHECK_INTERVAL)

        current_ips = fetch_ips()

        changed = []
        for key, value in current_ips.items():
            if previous_ips[key] != value:
                changed.append(key)
                previous_ips[key] = value

        '''
        #DEBUG for testing:
        print(f"Loop #{loopcounter}") #debug
        changed = []
        if loopcounter == 1:
            print("DEBUG: emulating docker IP change")
            changed.append(DOCKER_CONTAINER)
        elif loopcounter == 2:
            print("DEBUG: emulating public IP change")
            changed.append("public")
        elif loopcounter == 3:
            print("DEBUG: emulating local IP change")
            changed.append("local")
        elif loopcounter == 4:
            print("DEBUG: emulating changed docker IP = public IP")
            changed.append(DOCKER_CONTAINER)
            current_ips["public"] = "127.0.0.1"
            current_ips[DOCKER_CONTAINER] = "127.0.0.1"
        elif loopcounter == 5:
            print("DEBUG: emulating changed public IP = docker IP")
            changed.append("public")
            current_ips["public"] = "127.0.0.1"
            current_ips[DOCKER_CONTAINER] = "127.0.0.1"
        elif loopcounter == 6:
            print("DEBUG: exiting")
            exit()
        #DEBUG end
        '''

        # Update files and log changes if any
        if changed:
            for key in changed:
                if key == "local":
                    # Notify when local IP changes
                    message = f"IP changes detected\n\nlocal IP: {current_ips['local']} (changed)\npublic IP: {current_ips['public']}\n{DOCKER_CONTAINER} IP: {current_ips[DOCKER_CONTAINER]} {get_ip_location(current_ips[DOCKER_CONTAINER])}"
                    send_telegram_message(message)
                    log_message(f"{key} IP:{' ' * (spacing_length - 5)}{current_ips['local']} (changed)")
                elif key == "public":
                    # Notify when public IP changes and matches DOCKER_CONTAINER IP (idk why this would happen but including for completionism)
                    if current_ips["public"] == current_ips[DOCKER_CONTAINER]:
                        message = f"🚨 IP changes detected 🚨\n\nlocal IP: {current_ips['local']}\npublic IP: {current_ips['public']} (changed)\n{DOCKER_CONTAINER} IP: {current_ips[DOCKER_CONTAINER]} ({get_ip_location(current_ips[DOCKER_CONTAINER])})"
                        send_telegram_message(message)
                        log_message(f"{key} IP:{' ' * (spacing_length - len(key))}{value} (changed and same as {DOCKER_CONTAINER} IP) 🚨🚨🚨")
                    else:
                        # Regular notify
                        message = f"IP changes detected\n\nlocal IP: {current_ips['local']}\npublic IP: {current_ips['public']} (changed)\n{DOCKER_CONTAINER} IP: {current_ips[DOCKER_CONTAINER]} {get_ip_location(current_ips[DOCKER_CONTAINER])}"
                        send_telegram_message(message)
                        log_message(f"{key} IP:{' ' * (spacing_length - 6)}{current_ips['public']} (changed)")
                elif key == DOCKER_CONTAINER:
                    # Notify when DOCKER_CONTAINER IP changes and matches public IP
                    if current_ips["public"] == current_ips[DOCKER_CONTAINER]:
                        message = f"🚨 IP changes detected 🚨\n\nlocal IP: {current_ips['local']}\npublic IP: {current_ips['public']}\n{DOCKER_CONTAINER} IP: {current_ips[DOCKER_CONTAINER]} ({get_ip_location(current_ips[DOCKER_CONTAINER])}) (changed)"
                        send_telegram_message(message)
                        log_message(f"{key} IP:{' ' * (spacing_length - len(key))}{value} ({get_ip_location(value)}) (changed and same as public IP) 🚨🚨🚨")
                    else:
                        message = f"{key} IP changed to {current_ips[key]} (changed)"
                        # send_telegram_message(message)# Not sending if public IP != docker IP
                        log_message(f"{key} IP:{' ' * (spacing_length - len(key))}{value} ({get_ip_location(value)}) (changed)")

            # Update the IP file
            with open(ips_file, "w") as f:
                for key, value in current_ips.items():
                    f.write(f"{key}: {value}\n")

if __name__ == "__main__":
    main()
