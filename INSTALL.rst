Open Wob API install notes
######################################

.. contents::

Installation instructions
=============

Install using Docker
------------

Using `Docker Compose<https://docs.docker.com/compose/install/>`_ is by far the easiest way to spin up a development environment and get started with contributing to the Open Wob API. The following has been tested to work with Docker 1.0.1 and up.

1. Clone the Open Wob API git repository::

   $ git clone https://github.com/openstate/open-wob-api.git
   $ cd open-wob-api/

(optional) if you are developing then add the following line to the ``backend`` service in ``docker-compose.yml`` (e.g., below the ``mem_limit`` line); this will automatically reload changed files in Celery::

   command: /opt/owa/bin/backend.sh


2. Build and start the containers::

   $ docker-compose up -d

Elasticsearch is now accessible locally in the Docker container via http://127.0.0.1:9200, or from the host via http://<CONTAINER IP ADDRESS>:9200 (look up the container's IP address using ``docker inspect`` as shown below).

Some useful Docker commands::

   # Show all docker images on your machine
   $ docker images

   # List all containers which are currently running
   $ docker ps

   # List all containers
   $ docker ps -a

   # Connect another shell to a currently running container (useful during development)
   $ docker exec -it <CONTAINER ID/NAME> bash

   # Start a stopped container and automatically attach to it (-a)
   $ docker start -a <CONTAINER ID/NAME>

   # Attach to a running container (use `exec` though if you want to open any extra shells beyond this one)
   $ docker attach <CONTAINER ID/NAME>

   # Return low-level information on a container or image (e.g., a container's IP address)
   $ docker inspect <CONTAINER/IMAGE ID/NAME>

   Also, if attached to a container, either via run, start -a or attach, you can detach by typing CTRL+p CTRL+q

Usage
============

Some quick notes on how to use the Open Wob API

Running an Open Wob API extractor
------------

1. Make the necessary changes to the 'sources' settings file (``ocd_backend/sources.json``). For example, fill out any API keys you might need for specific APIs.

2. Start worker processes::

   $ celery --app=ocd_backend:celery_app worker --loglevel=info --concurrency=2

3. In another terminal (in case of Docker, use ``docker exec`` as described above), start the extraction process::

   $ ./manage.py extract start <name_of_source>

   You can get an overview of the available sources by running ``./manage.py extract list_sources``.

Automatic updating using cron
------------

The ``update.sh`` script contains the instructions to update indices. On the host machine run ``sudo crontab -e`` and add the following line::

   $ 0 1,7,13,19 * * * sudo docker exec open-wob-api_backend_1 ./opt/owa/update.sh
