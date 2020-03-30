#!/bin/sh
curl -s 'https://api.poliscoops.com/v0/search' -d '{"size": 0,"filters":{"type":{"terms":["Note"]}}}'
