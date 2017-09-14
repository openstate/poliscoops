#!/bin/sh

source /opt/bin/activate
cd /opt/owa
./manage.py extract start utrecht_new
./manage.py extract start utrecht_categories
