#!/bin/sh

source /opt/bin/activate
cd /opt/pfl

# controls how often we get things.
# if we want a different cycle for FB and non-FB we need to redo a part of
# the script since the logic is now based on a .updating file. could make
# a FB speciic part of that.
PFL_FB_CYCLES=48
PFL_WEB_CYCLES=24

# if we're not updating we should prepare for updating
if [ ! -e .updating ];
then
  echo "Creating updating files"
  touch .updating

  # split for non FB sources
  ./manage.py extract list_sources 2>/dev/null | grep -v '_archives_' | grep -v '_fb_' |awk '{print $2}' | sed 1d >.updating-sources
  PFL_NUM_SOURCES=`cat .updating-sources |wc -l`
  # Aim to crawl everything every 6 hours. At 4 times per hour this is 24 cycles
  PFL_BLOCK_SIZE=`expr $PFL_NUM_SOURCES / $PFL_WEB_CYCLES + 1`
  split -l $PFL_BLOCK_SIZE .updating-sources .updating-sources-
fi

if [ ! -e .updating-facebook ];
then
  touch .updating-facebook
  # split for FB sources
  ./manage.py extract list_sources 2>/dev/null | grep -v '_archives_' | grep '_fb_' |awk '{print $2}' | sed 1d >.updating-facebook-sources
  PFL_NUM_SOURCES=`cat .updating-facebook-sources |wc -l`
  # Aim to crawl everything every 6 hours. At 4 times per hour this is 24 cycles
  PFL_BLOCK_SIZE=`expr $PFL_NUM_SOURCES / $PFL_FB_CYCLES + 1`
  split -l $PFL_BLOCK_SIZE .updating-facebook-sources .updating-facebook-sources-
fi


# update non FB sources
PFL_CURRENT_FILE=`ls -1 .updating-sources-* 2>/dev/null |head -1`

if [ -n "$PFL_CURRENT_FILE" ];
then
  PFL_BUSY_FILE=`echo -n "$PFL_CURRENT_FILE" |sed -e 's/sources/busy/;'`
  mv "$PFL_CURRENT_FILE" "$PFL_BUSY_FILE"
  # Update all sources but not their archives (i.e., only the most recent articles)
  echo "Starting extraction of $PFL_BUSY_FILE"
  cat $PFL_BUSY_FILE | xargs -I{} ./manage.py extract start {}
  echo "Removing $PFL_BUSY_FILE"
  rm -f $PFL_BUSY_FILE
  echo "Removed $PFL_BUSY_FILE"
fi

# update FB sources
PFL_CURRENT_FILE=`ls -1 .updating-facebook-sources-* 2>/dev/null |head -1`

if [ -n "$PFL_CURRENT_FILE" ];
then
  PFL_BUSY_FILE=`echo -n "$PFL_CURRENT_FILE" |sed -e 's/sources/busy/;'`
  mv "$PFL_CURRENT_FILE" "$PFL_BUSY_FILE"
  # Update all sources but not their archives (i.e., only the most recent articles)
  echo "Starting extraction of $PFL_BUSY_FILE"
  while read -r PFL_SOURCE; do
    ./manage.py extract start "$PFL_SOURCE"
    sleep 1  # FB needs to sleep a little
  done <$PFL_BUSY_FILE
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

PFL_NUM_LEFT=`ls -1 .updating-facebook-sources-* 2>/dev/null |wc -l`
if [ $PFL_NUM_LEFT -eq 0 ];
then
  echo "No FB spool files left so removing updating indicator"
  rm -f .updating-facebook
  rm -f .updating-facebook-busy-*
fi

# Update archives of all sources (i.e., everything)
#./manage.py extract list_sources | grep '_archives_' | awk '{print $2}' | sed 1d | xargs -I{} ./manage.py extract start {}

# Update archives of all sources except those from CDA due to rate limiting
#./manage.py extract list_sources | grep '_archives_' | awk '{print $2}' | sed 1d | grep -v '^cda_archives_' | xargs -I{} ./manage.py extract start {}
