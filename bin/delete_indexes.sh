#!/bin/sh
curl -XDELETE 'http://elasticsearch:9200/owa_combined_index/'
curl -XDELETE 'http://elasticsearch:9200/owa_utrecht/'
