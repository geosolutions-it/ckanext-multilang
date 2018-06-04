#!/bin/sh -e

nosetests --ckan --nologcapture --with-pylons=subdir/test.ini --with-coverage --cover-package=ckanext.multilang --cover-inclusive --cover-erase --cover-tests
