import os
import time
import requests
import subprocess
from datetime import datetime

# Load environment variables
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30)) * 60
DOCKER_CONTAINER = os.getenv("DOCKER_CONTAINER")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_RECEIVER = os.getenv("TELEGRAM_RECEIVER")

log_file = "/app/public-ips.log"
ips_file = "/app/public-ips.txt"

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - {message}\n"
    with open(log_file, "a") as f:
        f.write(log_entry)
    # Log to Docker logs
    print(log_entry, end="")

def get_ip_location(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        if response.status_code == 200:
            data = response.json()
            city = data.get("city", "Unknown City")
            region = data.get("region", "Unknown Region")
            country = data.get("country", "Unknown Country")
            location_string = f"{city}, {region}, {country}"
            if country == "country" and region == "region" and city == "city":
                log_message(f"Something went wrong while location fetching.\nresponse.json: {data}")
                return "Unable to fetch location (1)"
            return location_string
        else:
            log_message(f"Could not fetch location from ipinfo.io, {reponse}, {response.text}")
            return "Unable to fetch location (2)"
    except Exception as e:
        log_message(f"Exception while fetching location data: {e}")
        return "Unable to fetch location (3)"

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org").text
    except Exception as e:
        log_message(f"Failed to get public IP: {e}")
        return str(e)

def get_router_ip():
    # unused, because public router and public device IP are the same
    try:
        return requests.get("https://api.ipify.org", proxies={"http": "http://192.168.2.1"}).text
    except Exception as e:
        log_message(f"Failed to get router IP: {e}")
        return str(e)

def get_local_ip():
    try:
        return subprocess.check_output(["hostname", "-I"]).decode().split()[0]
    except Exception as e:
        log_message(f"Failed to get local IP (1): {e}")
    try:
        ipconfig_en1 = subprocess.check_output(["ipconfig", "getifaddr", "en0"]).decode().strip()
        if len(ipconfig_en0) > 1: return ipconfig_en0
    except Exception as e:
        log_message(f"Failed to get local IP (2): {e}")
    try:
        ipconfig_en1 = subprocess.check_output(["ipconfig", "getifaddr", "en1"]).decode().strip()
        if len(ipconfig_en1) > 1: return ipconfig_en1
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
            ip = result.stdout.decode().strip()
            ip_location = get_ip_location(ip)
            return f"{ip} ({ip_location})"
        else:
            raise Exception(result.stderr.decode().strip())
    except Exception as e:
        log_message(f"Failed to get IP for container {container_name}: {e}")
        return str(e)

def send_telegram_message(message):
    try:
        message += f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_RECEIVER, "text": message}
        telegramresponse = requests.post(url, data=payload)
        if "200" not in str(telegramresponse): log_message(f"Telegram Reponse: {telegramresponse.text} / {telegramresponse}")
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
    # Log initial IPs
    try:
        for key, value in initial_ips.items():
            log_message(f"Initial {key} IP: {value}")
    except Exception as e:
        log_message(f"Failed to log initial IPs: {e}")
    # Write initial IPs
    try:
        with open(ips_file, "w") as f:
            for key, value in initial_ips.items():
                f.write(f"{key}: {value}\n")
    except Exception as e:
        log_message(f"Failed to write initial IPs: {e}")
    # Initial Telegram message
    try:
        initialmessage = "Watchdog started\n\n"
        for key, value in initial_ips.items():
            initialmessage += f"{key} IP: {value}\n"
        send_telegram_message(initialmessage)
    except Exception as e:
        log_message(f"Failed to send initial Telegram message: {e}")

    # Return initial IPs (to be used as previous_ips)
    return initial_ips

def main():
    global previous_ips
    previous_ips = {"local": "", "public": "", "router": "", f"{DOCKER_CONTAINER}": ""}

    log_message("Starting IP Checker...")

    previous_ips = initial_messaging()

    if CHECK_INTERVAL > 0:
        log_message(f"Starting loop with CHECK_INTERVAL {CHECK_INTERVAL} seconds")
    else:
        log_message(f"CHECK_INTERVAL was set to 0. exiting")
        exit()

    while True:
        time.sleep(CHECK_INTERVAL)
        
        current_ips = fetch_ips()

        # Check for changes
        changed = []
        for key, value in current_ips.items():
            if previous_ips[key] != value:
                changed.append(key)
                previous_ips[key] = value

        # Update files and log changes if any
        if changed:
            for key in changed:
                log_message(f"{key} IP changed to {current_ips[key]}")
            with open(ips_file, "w") as f:
                for key, value in current_ips.items():
                    f.write(f"{key}: {value}\n")
            send_telegram_message(
                f"IP changes detected:\n\n" + "\n".join([f"{key}: {current_ips[key]}" for key in changed])
            )

if __name__ == "__main__":
    main()
