#!/bin/sh

source /opt/bin/activate
cd /opt/owa
./bin/download_overview.sh
./manage.py extract start utrecht_overview
./manage.py extract start utrecht_new
./manage.py extract start utrecht_categories
./bin/send_emails.py
