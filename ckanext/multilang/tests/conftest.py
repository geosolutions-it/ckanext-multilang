# -*- coding: utf-8 -*-

import pytest
import os
import re
from sqlalchemy import Table

from ckan.model import Session
import ckanext.harvest.model as harvest_model
from ckanext.multilang.model import setup as db_setup


@pytest.fixture
def create_postgis_tables():
    Session.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    Session.commit()


@pytest.fixture
def clean_postgis():
    Session.execute("DROP TABLE IF EXISTS package_multilang")
    Session.execute("DROP TABLE IF EXISTS resource_multilang")
    Session.execute("DROP TABLE IF EXISTS tag_multilang")
    Session.execute("DROP TABLE IF EXISTS group_multilang")
    Session.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
    Session.commit()


@pytest.fixture
def harvest_setup():
    harvest_model.setup()


@pytest.fixture
def multilang_setup():
    db_setup()
