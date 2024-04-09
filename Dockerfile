from python:latest
RUN pip install requests

WORKDIR /opt/tesla-invoices
COPY download_v2.py .

# to refresh the access token every 2 hours
COPY refresh.sh .
RUN apt update
RUN apt install -y cron jq
RUN crontab -l | { cat; echo "*/2 * * * * bash /opt/tesla-invoices/refresh.sh"; } | crontab -

ENTRYPOINT ["cron", "tail", "-f", "/dev/null"]