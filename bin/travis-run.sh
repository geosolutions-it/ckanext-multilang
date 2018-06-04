#!/bin/sh -e
set -e
set -x

nosetests --ckan --nologcapture --with-pylons=subdir/test.ini --with-coverage --cover-package=ckanext.multilang --cover-inclusive --cover-erase --cover-tests ckanext/multilang
