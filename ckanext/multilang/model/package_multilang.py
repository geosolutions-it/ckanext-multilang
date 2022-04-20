import logging

from sqlalchemy import Column, ForeignKey, Table, types

from ckan.model import Session, meta
from ckan.model.domain_object import DomainObject

__all__ = [
    'PackageMultilang',
    'package_multilang_table',
    'GroupMultilang',
    'ResourceMultilang',
    'group_multilang_table',
    'TagMultilang',
    'tag_multilang_table',
    'setup_db',
]

log = logging.getLogger(__name__)


package_multilang_table = Table('package_multilang', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('package_id', types.UnicodeText, ForeignKey('package.id', ondelete='CASCADE'), nullable=False),
    Column('field', types.UnicodeText, nullable=False, index=True),
    Column('field_type', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=False))

group_multilang_table = Table('group_multilang', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('group_id', types.UnicodeText, ForeignKey('group.id', ondelete='CASCADE'), nullable=False),
    Column('name', types.UnicodeText, nullable=False, index=True),
    Column('field', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=False))

resource_multilang_table = Table('resource_multilang', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('resource_id', types.UnicodeText, ForeignKey('resource.id', ondelete='CASCADE'), nullable=False),
    Column('field', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=False))

tag_multilang_table = Table('tag_multilang', meta.metadata,
    Column('id', types.Integer, primary_key=True),
    Column('tag_id', types.UnicodeText, ForeignKey('tag.id', ondelete='CASCADE'), nullable=False),
    Column('tag_name', types.UnicodeText, nullable=False, index=True),
    Column('lang', types.UnicodeText, nullable=False, index=True),
    Column('text', types.UnicodeText, nullable=False, index=False))


def setup_db():
    # log.debug('Multilingual tables defined in memory')
    created = False

    for t in (package_multilang_table,
              group_multilang_table,
              resource_multilang_table,
              tag_multilang_table,
              ):

        if t.exists():
            log.debug(f'MultiLang: table {t.name} already exists')
        else:
            try:
                log.info(f'MultiLang: creating table {t.name}')
                t.create()
                created = True
            except Exception as e:
                # Make sure the table does not remain incorrectly created
                if t.exists():
                    Session.execute(f'DROP TABLE {t.name}')
                    Session.commit()
                raise e

    return created


class PackageMultilang(DomainObject):
    def __init__(self, package_id=None, field=None, field_type=None, lang=None, text=None):
        self.package_id = package_id
        self.field = field
        self.lang = lang
        self.field_type = field_type
        self.text = text

    @classmethod
    def get(self, pkg_id, field, pkg_lang, field_type):
        obj = meta.Session.query(self).autoflush(False)
        record = obj.filter_by(package_id=pkg_id, field=field, lang=pkg_lang, field_type=field_type).first()
        return record

    @classmethod
    def get_for_package(self, package_id):
        obj = meta.Session.query(self).autoflush(False)
        records = obj.filter(self.package_id == package_id).all()
        return records

    @classmethod
    def get_for_package_id_and_lang(self, pkg_id, pkg_lang):
        obj = meta.Session.query(self).autoflush(False)
        records = obj.filter_by(package_id=pkg_id, lang=pkg_lang)
        return records

    @classmethod
    def persist(self, package, lang, field_type='package'):
        session = meta.Session
        try:
            session.add_all([
                PackageMultilang(package_id=package.get('id'), field=package.get('field'), field_type=field_type, lang=lang, text=package.get('text')),
            ])

            session.commit()
        except Exception as e:
            # on rollback, the same closure of state
            # as that of commit proceeds.
            session.rollback()

            log.error('Exception occurred while persisting DB objects:', exc_info=e)
            raise


meta.mapper(PackageMultilang, package_multilang_table)


class GroupMultilang(DomainObject):
    def __init__(self, group_id=None, name=None, field=None, lang=None, text=None):
        self.group_id = group_id
        self.name = name
        self.field = field
        self.lang = lang
        self.text = text

    @classmethod
    def get_for_group_id(self, group_id):
        obj = meta.Session.query(self).autoflush(False)
        records = obj.filter(self.group_id == group_id).all()
        return records

    @classmethod
    def get_for_group_id_and_lang(self, group_id, group_lang):
        obj = meta.Session.query(self).autoflush(False)
        records = obj.filter_by(group_id=group_id, lang=group_lang)
        return records

    @classmethod
    def get_for_group_name(self, group_name):
        obj = meta.Session.query(self).autoflush(False)
        records = obj.filter_by(name=group_name)
        return records

    @classmethod
    def get_for_group_name_and_lang(self, group_name, group_lang):
        obj = meta.Session.query(self).autoflush(False)
        records = obj.filter_by(name=group_name, lang=group_lang)
        return records

    @classmethod
    def persist(cls, group, lang):
        session = meta.Session
        try:
            session.add_all([
                cls(group_id=group.get('id'), name=group.get('name'), field='title', lang=lang, text=group.get('title')),
                cls(group_id=group.get('id'), name=group.get('name'), field='description', lang=lang, text=group.get('description')),
            ])

            session.commit()
        except Exception as e:
            # on rollback, the same closure of state
            # as that of commit proceeds.
            session.rollback()

            log.error('Exception occurred while persisting DB objects:', exc_info=e)
            raise


meta.mapper(GroupMultilang, group_multilang_table)


class ResourceMultilang(DomainObject):
    def __init__(self, resource_id=None, field=None, lang=None, text=None):
        self.resource_id = resource_id
        self.field = field
        self.lang = lang
        self.text = text

    @classmethod
    def get_for_pk(self, resource_id, field, lang):
        obj = meta.Session.query(self).autoflush(False)
        records = obj.filter_by(resource_id=resource_id, field=field, lang=lang).all()
        if len(records) > 1:
            log.error('Too many ResourceMultilang records: %s', records)
            return records[0]
        elif len(records) == 1:
            return records[0]
        else:
            return None

    @classmethod
    def get_for_resource_id(self, resource_id):
        obj = meta.Session.query(self).autoflush(False)
        records = obj.filter_by(resource_id=resource_id)
        return records

    @classmethod
    def get_for_resource_id_and_lang(self, res_id, res_lang):
        obj = meta.Session.query(self).autoflush(False)
        records = obj.filter_by(resource_id=res_id, lang=res_lang)
        return records

    @classmethod
    def persist(self, resource, lang):
        session = meta.Session
        try:
            name = resource.get('name')
            desc = resource.get('description') or ''
            session.add_all([
                self(resource_id=resource.get('id'), field='name', lang=lang, text=name),
                self(resource_id=resource.get('id'), field='description', lang=lang, text=desc),
            ])

            session.commit()
        except Exception as e:
            # on rollback, the same closure of state
            # as that of commit proceeds.
            session.rollback()

            log.error('Exception occurred while persisting DB objects:', exc_info=e)
            raise

    @classmethod
    def persist_resources(self, resources_list):
        session = meta.Session
        try:
            session.add_all(resources_list)
            session.commit()
        except Exception as e:
            # on rollback, the same closure of state
            # as that of commit proceeds.
            session.rollback()

            log.error('Exception occurred while persisting DB objects:', exc_info=e)
            raise


meta.mapper(ResourceMultilang, resource_multilang_table)


class TagMultilang(DomainObject):
    def __init__(self, tag_id=None, tag_name=None, lang=None, text=None):
        self.tag_id = tag_id
        self.tag_name = tag_name
        self.lang = lang
        self.text = text

    @classmethod
    def get_all(cls, tag_name, tag_lang=None):
        query = meta.Session.query(TagMultilang).filter(TagMultilang.tag_name == tag_name)
        if tag_lang:
            query = query.filter(TagMultilang.lang == tag_lang)
        return query

    @classmethod
    def by_name(self, tag_name, tag_lang, autoflush=True):
        query = meta.Session.query(TagMultilang).filter(TagMultilang.tag_name == tag_name, TagMultilang.lang == tag_lang)
        query = query.autoflush(autoflush)
        tag = query.first()
        return tag

    @classmethod
    def all_by_name(self, tag_name, autoflush=True):
        query = meta.Session.query(TagMultilang).filter(TagMultilang.tag_name == tag_name)
        query = query.autoflush(autoflush)
        tags = query.all()

        ret = {}
        for record in tags:
            ret[record.lang] = record.text

        return ret

    @classmethod
    def by_tag_id(self, tag_id, tag_lang, autoflush=True):
        query = meta.Session.query(TagMultilang).filter(TagMultilang.tag_id == tag_id, TagMultilang.lang == tag_lang)
        query = query.autoflush(autoflush)
        tag = query.first()
        return tag

    @classmethod
    def persist(self, tag, lang):
        session = meta.Session
        try:
            session.add(
                TagMultilang(tag_id=tag.get('id'), tag_name=tag.get('name'), lang=lang, text=tag.get('text')),
            )

            session.commit()
        except Exception as e:
            # on rollback, the same closure of state
            # as that of commit proceeds.
            session.rollback()

            log.error('Exception occurred while persisting DB objects:', exc_info=e)
            raise

    @classmethod
    def save_tags(cls, *tags):
        session = meta.Session
        try:
            session.add_all([
                TagMultilang(
                    tag_id=tag.get('id'),
                    tag_name=tag.get('name'),
                    lang=tag.get('lang'),
                    text=tag.get('text'))
                for tag in tags
            ])

            session.commit()
        except Exception as e:
            # on rollback, the same closure of state
            # as that of commit proceeds.
            session.rollback()

            log.error('Exception occurred while persisting DB objects:', exc_info=e)
            raise


meta.mapper(TagMultilang, tag_multilang_table)
