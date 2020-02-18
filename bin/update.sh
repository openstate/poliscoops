#!/bin/sh

source /opt/bin/activate
cd /opt/pfl

# controls how often we get things. one cycle is 15 minutens
PFL_FB_CYCLES=48
PFL_WEB_CYCLES=24
PFL_EXTA_OPTS="--sources_config=ocd_backend/sources/eu/eu.json "
# if we're not updating we should prepare for updating
if [ ! -e .updating ];
then
  echo "Creating updating files"
  touch .updating

  # split for non FB sources
  ./manage.py extract list_sources $PFL_EXTRA_OPTS 2>/dev/null | grep -v '_archives_' | grep -v '_fb_' |awk '{print $2}' | sed 1d >.updating-sources
  PFL_NUM_SOURCES=`cat .updating-sources |wc -l`
  # Aim to crawl everything every 6 hours. At 4 times per hour this is 24 cycles
  PFL_BLOCK_SIZE=`expr $PFL_NUM_SOURCES / $PFL_WEB_CYCLES + 1`
  split -l $PFL_BLOCK_SIZE .updating-sources .updating-sources-
fi


# update non FB sources
PFL_CURRENT_FILE=`ls -1 .updating-sources-* 2>/dev/null |head -1`

if [ -n "$PFL_CURRENT_FILE" ];
then
  PFL_BUSY_FILE=`echo -n "$PFL_CURRENT_FILE" |sed -e 's/sources/busy/;'`
  mv "$PFL_CURRENT_FILE" "$PFL_BUSY_FILE"
  # Update all sources but not their archives (i.e., only the most recent articles)
  echo "Starting extraction of $PFL_BUSY_FILE"
  cat $PFL_BUSY_FILE | xargs -I{} ./manage.py extract start $PFL_EXTRA_OPTS {}
  echo "Removing $PFL_BUSY_FILE"
  rm -f $PFL_BUSY_FILE
  echo "Removed $PFL_BUSY_FILE"
fi


PFL_NUM_LEFT=`ls -1 .updating-sources-* 2>/dev/null |wc -l`
if [ $PFL_NUM_LEFT -eq 0 ];
then
  echo "No spool files left so removing updating indicator"
  rm -f .updating
  rm -f .updating-busy-*
fi
