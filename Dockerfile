FROM python:3.9-slim

# Install necessary tools
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y iproute2
# Installng requirements for docker functionality (checking container-specific IP)
RUN apt-get install -y gnupg2
RUN apt-get install -y software-properties-common
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian bullseye stable" > /etc/apt/sources.list.d/docker.list
RUN apt-get update
RUN apt-get install -y docker.io

RUN rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install requests

# Add the script to the container
WORKDIR /app
COPY check-ips.py .

# Run the script
CMD ["python", "-u", "/app/check-ips.py"]
