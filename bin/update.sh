#!/bin/sh

source /opt/bin/activate
cd /opt/pfl

# if we're not updating we should prepare for updating
if [ ! -e .updating ];
then
  echo "Creating updating files"
  touch .updating
  ./manage.py extract list_sources 2>/dev/null | grep -v '_archives_' | awk '{print $2}' | sed 1d >.updating-sources
  PFL_NUM_SOURCES=`cat .updating-sources |wc -l`
  # Aim to crawl everything every 6 hours. At 4 times per hour this is 24 cycles
  PFL_BLOCK_SIZE=`expr $PFL_NUM_SOURCES / 24 + 1`
  split -l $PFL_BLOCK_SIZE .updating-sources .updating-sources-
fi

PFL_CURRENT_FILE=`ls -1 .updating-sources-* 2>/dev/null |head -1`

if [ -n "$PFL_CURRENT_FILE" ];
then
  # Update all sources but not their archives (i.e., only the most recent articles)
  echo "Starting extraction of $PFL_CURRENT_FILE"
  cat $PFL_CURRENT_FILE | xargs -I{} ./manage.py extract start {}
  echo "Removing $PFL_CURRENT_FILE"
  rm -f $PFL_CURRENT_FILE
  echo "Removed $PFL_CURRENT_FILE"  
fi

PFL_NUM_LEFT=`ls -1 .updating-sources-* 2>/dev/null |wc -l`
if [ $PFL_NUM_LEFT -eq 0 ];
then
  echo "No spool files left so removing updating indicator"
  rm -f .updating
fi

# Update archives of all sources (i.e., everything)
#./manage.py extract list_sources | grep '_archives_' | awk '{print $2}' | sed 1d | xargs -I{} ./manage.py extract start {}

# Update archives of all sources except those from CDA due to rate limiting
#./manage.py extract list_sources | grep '_archives_' | awk '{print $2}' | sed 1d | grep -v '^cda_archives_' | xargs -I{} ./manage.py extract start {}
