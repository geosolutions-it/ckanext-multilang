
import sys
import logging

from sqlalchemy import types, Column, Table, ForeignKey
from sqlalchemy import orm

from ckan.lib.base import config
from ckan import model
from ckan.model import Session
from ckan.model import meta
from ckan.model.domain_object import DomainObject

from ckan import model

log = logging.getLogger(__name__)

__all__ = ['PackageMultilang', 'package_multilang_table', 'GroupMultilang', 'ResourceMultilang', 'group_multilang_table', 'setup']

package_multilang_table = Table('package_multilang', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('package_id', types.UnicodeText, ForeignKey("package.id", ondelete="CASCADE"), nullable=False),
    Column('field', types.UnicodeText, nullable=False, index=True),
    Column('field_type', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=True))

group_multilang_table = Table('group_multilang', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('group_id', types.UnicodeText, ForeignKey("group.id", ondelete="CASCADE"), nullable=False),
    Column('name', types.UnicodeText, nullable=False, index=True),
    Column('field', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=True))

resource_multilang_table = Table('resource_multilang', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('resource_id', types.UnicodeText, ForeignKey("resource.id", ondelete="CASCADE"), nullable=False),
    Column('field', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=True))

def setup():
    log.debug('Multilingual tables defined in memory')

    #Setting up package multilang table
    if not package_multilang_table.exists():
        try:
            package_multilang_table.create()
        except Exception,e:
            # Make sure the table does not remain incorrectly created
            if package_multilang_table.exists():
                Session.execute('DROP TABLE package_multilang')
                Session.commit()

            raise e

        log.info('Package Multilingual table created')
    else:
        log.info('Package Multilingual table already exist')
    
    #Setting up group multilang table
    if not group_multilang_table.exists():
        try:
            group_multilang_table.create()
        except Exception,e:
            # Make sure the table does not remain incorrectly created
            if group_multilang_table.exists():
                Session.execute('DROP TABLE group_multilang')
                Session.commit()

            raise e

        log.info('Group Multilingual table created')
    else:
        log.info('Group Multilingual table already exist')

    #Setting up resource multilang table
    if not resource_multilang_table.exists():
        try:
            resource_multilang_table.create()
        except Exception,e:
            # Make sure the table does not remain incorrectly created
            if resource_multilang_table.exists():
                Session.execute('DROP TABLE resource_multilang')
                Session.commit()

            raise e

        log.info('Resource Multilingual table created')
    else:
        log.info('Resource Multilingual table already exist')

class PackageMultilang(DomainObject):
    def __init__(self, package_id=None, field=None, field_type=None, lang=None, text=None):
        self.package_id = package_id
        self.field = field
        self.lang = lang
        self.field_type = field_type
        self.text = text

    @classmethod
    def get_for_package(self, package_id):
        log.debug("::::::::::::::::::: get_for_package:   %r", package_id)
        obj = meta.Session.query(self).autoflush(False)

        records = obj.filter_by(package_id=package_id)
        log.debug("::::::::::::::::::: records:   %r", records)
        
        return records

meta.mapper(PackageMultilang, package_multilang_table)

class GroupMultilang(DomainObject):
    def __init__(self, group_id=None, name=None, field=None, lang=None, text=None):
        self.group_id = group_id
        self.name = name
        self.field = field
        self.lang = lang
        self.text = text

meta.mapper(GroupMultilang, group_multilang_table)

class ResourceMultilang(DomainObject):
    def __init__(self, resource_id=None, field=None, lang=None, text=None):
        self.resource_id = resource_id
        self.field = field
        self.lang = lang
        self.text = text

meta.mapper(ResourceMultilang, resource_multilang_table)