# Public-IP-Checker
Built as a docker container that monitors the local and public IP of the devoce as well as the public IP and IP location of a user-specified docker container. With Telegram notification.

Built, tested and deployed on a Raspberry Pi 4 running Raspbian 12 (bookworm)

## What?
Checks once at startup and then every x minutes (user-specified) for:
- local IP (of the device)
- public IP (of the device)
- public IP of a user-specified docker container
- geolocation of container IP

Notifies the user via Telegram about the initial IPs and then, if something has changed.

## Why?
Monitoring the public IP is useful for remote access if you don't want to use dynDNS services.

Monitoring the IP and IP-location of a specific docker container is useful if you're running a VPN, for example.

## How?

### 1. Set up Telegram bot
1. Use Telegram's Botfather to create a Telegram bot: https://web.telegram.org/k/#@BotFather
2. Write down the bot username and bot-token
3. Go to https://api.telegram.org/bot<INSERT_TOKEN>/getUpdates and leave it open
4. Send a message from your phone or the web interface to the bot
5. Refresh the API website and write down the IP (is found in the string like this: "message_id":28,"from":{"id":<ID_YOU_NEED>,...")

> [!TIP]
> Detailled tutorial on Telegram bot creation: [https://core.telegram.org/bots/tutorial](https://core.telegram.org/bots/tutorial)


### 2. Download / Create files necessary and build the image
#### Method A: Build directly from this repo
```
docker build -t public-ip-checker https://github.com/induna-crewneck/Public-IP-Checker.git
```
#### Methid B: More manual
1. Download/upload the check_ips.py and Dockerfile from this repo to your device, either manually or by running
```
git clone https://github.com/induna-crewneck/Public-IP-Checker.git
```
2. `cd` into the directory where the files have been downloaded/uploaded to. If you used `git clone` it would be
```
cd Public-IP-Checker
```
3. Build the image
```
docker build -t public-ip-checker .
```

### 3. Create and run the container
#### Method A: `docker run` (Tested)
```
sudo docker run -d \
--name public-ip-checker \
--restart unless-stopped \
-e CHECK_INTERVAL=<how often you want to run the checks in minutes> \
-e DOCKER_CONTAINER=<the docker container you want to know the ip and location of> \
-e TELEGRAM_BOT_TOKEN=<the token you wrote down> \
-e TELEGRAM_RECEIVER=<the ID you wrote down> \
-v /var/run/docker.sock:/var/run/docker.sock \
public-ip-checker
```
Example:
```
sudo docker run -d \
--name public-ip-checker \
--restart unless-stopped \
-e CHECK_INTERVAL=30 \
-e DOCKER_CONTAINER=opvpn \
-e TELEGRAM_BOT_TOKEN=4017494205:15J1BjVpLidojAENI-p9Qh-e9ts4x51rfg6 \
-e TELEGRAM_RECEIVER=672951658 \
-v /var/run/docker.sock:/var/run/docker.sock \
public-ip-checker
```
> [!NOTE]
> You can set CHECK_INTERVAL to 0 if you want it to run only once for testing or if you want to only run this on-demand.

> [!WARNING]
> If for some reason your docker isn't located at `/var/run/`, change the first part of that line accordingly.

#### Method B: `docker create` and `docker start` (Untested, but should work, I guess)
```
sudo docker create \
--name public-ip-checker \
--restart unless-stopped \
-e CHECK_INTERVAL=30 \
-e DOCKER_CONTAINER=opvpn \
-e TELEGRAM_BOT_TOKEN=4017494205:15J1BjVpLidojAENI-p9Qh-e9ts4x51rfg6 \
-e TELEGRAM_RECEIVER=672951658 \
-v /var/run/docker.sock:/var/run/docker.sock \
public-ip-checker

sudo docker start public-ip-checker
```

### 4. Finnish
You're all set! You should have gotten a telegram message telling you what all the IPs are.

> [!TIP]
> If you want to check the progress or the logs, you can run `docker logs public-ip-checker`
