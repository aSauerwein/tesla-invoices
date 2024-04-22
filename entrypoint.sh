#!/bin/bash
printenv >> /etc/environment
if [ -f "/data/options.json" ]; then
    # running in HA, start webserver
    caddy file-server --browse --root /data/invoices/ --listen :9000 & 
fi

# trigger download once on startup
/usr/local/bin/python3 /opt/tesla-invoices/download_v2.py daemon > /proc/1/fd/1 2>&1
cron -f