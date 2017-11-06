#!/bin/sh

source /opt/bin/activate
cd /opt/pfl

/opt/bin/celery flower --app=ocd_backend:celery_app &
/opt/bin/celery multi start 1 -A ocd_backend:celery_app -l info --logfile=log/celery.log -c8 --pidfile=/var/run/celery/%n.pid

while true
  do
    inotifywait -e modify,attrib,close_write,move,delete --exclude 'temp\/' -r /opt/pfl/ocd_backend && date && source /opt/bin/activate && /opt/bin/celery multi restart 1 -A ocd_backend:celery_app --logfile=log/celery.log --pidfile=/var/run/celery/%n.pid
    sleep 10
  done
