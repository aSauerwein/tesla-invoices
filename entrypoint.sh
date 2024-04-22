#!/bin/bash
printenv >> /etc/environment
# trigger download once on startup
/usr/local/bin/python3 /opt/tesla-invoices/download_v2.py daemon > /proc/1/fd/1 2>&1
cron -f