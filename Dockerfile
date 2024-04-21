from python:latest
RUN pip install requests

WORKDIR /opt/tesla-invoices
COPY download_v2.py .

# to refresh the access token every 2 hours
RUN apt update
RUN apt install -y cron
COPY crontab /etc/cron.d/
RUN crontab /etc/cron.d/crontab
COPY entrypoint.sh .
ENTRYPOINT ["/opt/tesla-invoices/entrypoint.sh"]