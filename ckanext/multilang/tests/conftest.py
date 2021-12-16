# -*- coding: utf-8 -*-

import pytest

from ckan.tests.pytest_ckan.fixtures import clean_db
from ckanext.harvest.tests.fixtures import harvest_setup
from ckanext.spatial.tests.conftest import clean_postgis, spatial_setup
from ckanext.multilang.model import setup_db as multilang_setup_db


@pytest.fixture
def multilang_setup():
    multilang_setup_db()


@pytest.fixture
def clean_multilang_db(clean_postgis, clean_db, harvest_setup, spatial_setup, multilang_setup):
    return [
        clean_postgis,
        clean_db,
        # clean_index()
        harvest_setup,
        spatial_setup,
        multilang_setup,
        ]
