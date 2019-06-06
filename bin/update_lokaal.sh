#!/bin/sh
for s in `./manage.py extract list_sources --sources_config=ocd_backend/sources/lokaal.json |awk '{print $2}'`;
do
  ./manage.py extract start "$s" --sources_config=ocd_backend/sources/lokaal.json
done
