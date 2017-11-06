#!/bin/sh

source /opt/bin/activate
cd /opt/pfl
./bin/download_overview.sh
#./manage.py extract start <source>
./bin/send_emails.py
