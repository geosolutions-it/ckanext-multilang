import click

from ckanext.multilang.model import setup as db_setup


@click.group()
def multilang():
    pass


@multilang.command()
def initdb():
    '''Performs multilingual related operations.

    Usage:
        multilang initdb []
            Creates the necessary tables.

    The commands should be run from the ckanext-multilang directory and expect
    a development.ini file to be present. Most of the time you will
    specify the config explicitly though::

        paster extents update --config=../ckan/development.ini

    :return:
    '''
    db_setup()
    click.secho('Multilingual DB tables created', fg=u"green")
