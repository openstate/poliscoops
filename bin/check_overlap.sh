#!/bin/sh
curl -sXPOST 'http://elasticsearch:9200/owa_combined_index/_search' -d '{"query":{"bool":{"must":[{"exists":{"field":"start_date"}},{"exists":{"field":"end_date"}}]}},"size":0}'
