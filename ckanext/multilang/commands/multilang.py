import sys
import re
from pprint import pprint
import logging

from ckan.lib.cli import CkanCommand
from ckan.lib.helpers import json

log = logging.getLogger(__name__)

class Multilang(CkanCommand):
    '''Performs multilingual related operations.

    Usage:
        multilang initdb []
            Creates the necessary tables.
      
    The commands should be run from the ckanext-multilang directory and expect
    a development.ini file to be present. Most of the time you will
    specify the config explicitly though::

        paster extents update --config=../ckan/development.ini

    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2 
    min_args = 0

    def command(self):
        self._load_config()
        print ''

        if len(self.args) == 0:
            self.parser.print_usage()
            sys.exit(1)
        cmd = self.args[0]
        if cmd == 'initdb':
            self.initdb()
        elif cmd == "initsearch":
            self.initsearch()
        else:
            print 'Command %s not recognized' % cmd

    def initdb(self):
        from ckanext.multilang.model import setup as db_setup
        
        db_setup()

        #print 'Multilingual DB tables created'

    def initsearch(self):
        from ckan.lib.search.common import make_connection

        conn = make_connection()
        path = "schema"
        dynamic_field = b'{"add-dynamic-field": {"name": ' \
                        b'"package_multilang_localized_*",' \
                        b'"type": "text", "indexed": "true", ' \
                        b'"stored": "true", "multiValued": "false"}}'
        res = conn._send_request("post", path, dynamic_field)
        log.debug("Result of dynamic field addition {result}".format(
            result=res))

        copy_field = b'{"add-copy-field":{' \
                     b'"source": "package_multilang_localized_*",  ' \
                     b'"dest": "text"}}'

        res = conn._send_request("post", path, copy_field)
        log.debug("Result of copy field addition {result}".format(result=res))
        pass

