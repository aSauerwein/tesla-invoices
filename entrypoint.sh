#!/bin/bash
print "Start Tesla-Invoices hourly cron job"
printenv >> /etc/environment
cron -f