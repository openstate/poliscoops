Poliscoops API install notes
######################################

.. contents::

Installation instructions
=============

Install using Docker
------------

Using `Docker Compose <https://docs.docker.com/compose/install/>`_ is by far the easiest way to spin up a development environment and get started with contributing to Poliscoops. The following has been tested to work with Docker 1.0.1 and up.

1. Clone the Poliscoops git repository::

   $ git clone https://github.com/openstate/poliscoops.git
   $ cd poliflw/docker

2. Build and start the containers::

If you're in production::

   $ docker-compose up -d

If you're in development::

   $ docker-compose -f docker-compose.yml -f docker-compose-dev.yml up -d

Elasticsearch is now accessible locally in the Docker container via http://127.0.0.1:9200, or from the host via http://<CONTAINER IP ADDRESS>:9200 (look up the container's IP address using ``docker inspect`` as shown below).

Furthermore, to make everything ready for getting sources and using it locally, you need to do the following::

   $ docker exec -it pls_backend_1 bash
   $ source ../env/bin/activate
   $ ./manage.py elasticsearch put_template
   $ ./manage.py elasticsearch create_indexes es_mappings

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
Some quick notes on how to use the PoliFLW API

Compile assets
---------------
Install all packages (only need to run once after installation or when you change packages): `sudo docker exec poen_node_1 yarn`

Production
----------
Build CSS/JS to static/dist directory: `sudo docker exec poen_node_1 yarn prod`

Development
------------
- Build CSS/JS to static/dist directory (with map files): `sudo docker exec poen_node_1 yarn dev`
- Automatically build CSS/JS when a file changes (simply refresh the page in your browser after a change): `sudo docker exec poen_node_1 yarn watch`


Running an Poliscoops extractor
------------

1. Make the necessary changes to the 'sources' settings file (``ocd_backend/sources.json``). For example, fill out any API keys you might need for specific APIs.

2. In another terminal (in case of Docker, use ``docker exec`` as described above), start the extraction process::

   $ ./manage.py extract start <name_of_source>

   You can get an overview of the available sources by running ``./manage.py extract list_sources``.

Generating documentation
------------

To generate the documentation run::

   $ docker exec pfl_backend_1 sh -c "source ../bin/activate && cd docs && make html"

If you get permission errors then ``pls_nginx_1`` probably already created an empty ``_build/html`` directory. Simply delete this directory and run the command above again.

Automatic updating using cron
------------

The ``update.sh`` script contains the instructions to update indices. On the host machine run ``sudo crontab -e`` and add the following line::

   $ 0 1,7,13,19 * * * sudo docker exec pls_backend_1 /opt/pfl/bin/update.sh
