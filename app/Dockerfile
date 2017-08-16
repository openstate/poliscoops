FROM python:2.7
MAINTAINER Open State Foundation <developers@openstate.eu>

#Set Timezone
RUN echo "Europe/Amsterdam" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata

WORKDIR /opt/app
ADD requirements.txt .
RUN pip install -r requirements.txt

# Production
# CMD uwsgi --socket 0.0.0.0:5000 --processes 8 -w manage:app

# Development
ENV FLASK_APP=manage.py \
  FLASK_DEBUG=1
CMD flask run --host=0.0.0.0
