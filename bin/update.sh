#!/bin/sh

source /opt/bin/activate
cd /opt/pfl

# Update all sources but not their archives (i.e., only the most recent articles)
./manage.py extract list_sources | grep -v '_archives_' | awk '{print $2}' | sed 1d | xargs -I{} ./manage.py extract start {}

# Update archives of all sources (i.e., everything)
#./manage.py extract list_sources | grep '_archives_' | awk '{print $2}' | sed 1d | xargs -I{} ./manage.py extract start {}

# Update archives of all sources except those from CDA due to rate limiting
#./manage.py extract list_sources | grep '_archives_' | awk '{print $2}' | sed 1d | grep -v '^cda_archives_' | xargs -I{} ./manage.py extract start {}
