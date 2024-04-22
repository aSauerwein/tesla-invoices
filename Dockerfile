from python:latest
RUN pip install requests

WORKDIR /opt/tesla-invoices
COPY download_v2.py .

# to refresh the access token every 2 hours
RUN apt update
RUN apt install -y cron

# download caddy
RUN  apt install -y debian-keyring debian-archive-keyring apt-transport-https curl \
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' |  gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' |  tee /etc/apt/sources.list.d/caddy-stable.list
RUN apt update
RUN apt install -y caddy

COPY crontab /etc/cron.d/
RUN crontab /etc/cron.d/crontab
COPY entrypoint.sh .
ENTRYPOINT ["/opt/tesla-invoices/entrypoint.sh"]