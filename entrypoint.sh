#!/bin/bash
print "Start Tesla-Invocies hourly cron job"
printenv >> /etc/environment
cron -f