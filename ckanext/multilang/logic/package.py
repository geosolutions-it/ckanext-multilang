import logging

import ckanext.multilang.helpers as helpers
from ckanext.multilang.model import PackageMultilang, TagMultilang, GroupMultilang, ResourceMultilang

log = logging.getLogger(__name__)

# Managed localized fields for Package in package_multilang table
PKG_LOCALIZED_FIELDS = [
    'title',
    'notes',
    'author',
    'maintainer',
    'url'
]


def after_create_dataset(context, obj_dict, lang):
    log.info(f'--> after_create_dataset {obj_dict}')

    # #  MULTILANG - retrieving dict for localized tag's strings
    # extra_tag = None
    # if data_dict.get('extra_tag'):
    #     extra_tag = data_dict.get('extra_tag')
    #     # After saving in memory the extra_tag dict this must be removed because not present in the schema
    #     del data_dict['extra_tag']
    #
    # pkg_dict = get_action('package_create')(context, data_dict)
    #
    # #  MULTILANG - persisting tags
    # self.localized_tags_persist(extra_tag, pkg_dict, lang)

    # MULTILANG - persisting the localized package dict
    log.info('::::: Persisting localised metadata locale :::::')
    for field in PKG_LOCALIZED_FIELDS:
        if obj_dict.get(field):
            PackageMultilang.persist({'id': obj_dict.get('id'), 'field': field, 'text': obj_dict.get(field)}, lang)


def after_update_dataset(context, pkg_dict, lang):
    log.info(f'--> after_update_dataset {pkg_dict}')

    # #  MULTILANG - retrieving dict for localized tag's strings
    #  extra_tag = None
    #  if data_dict.get('extra_tag'):
    #      extra_tag = data_dict.get('extra_tag')
    #      # After saving in memory the extra_tag dict this must be removed because not present in the schema
    #      del data_dict['extra_tag']

    # #  MULTILANG - persisting tags
    # self.localized_tags_persist(extra_tag, c.pkg_dict, lang)
    #
    # #  MULTILANG - persisting package dict
    # log.info(':::::::::::: Saving the corresponding localized title and abstract :::::::::::::::')

    # q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == c.pkg_dict.get('id'), PackageMultilang.lang == lang).all()

    pkg_id = pkg_dict.get('id')
    q_results = PackageMultilang.get_for_package_id_and_lang(pkg_id, lang)

    if q_results:
        pkg_processed_field = []
        for result in q_results:
            # do not update multilang field if original pkg dict doesn't have this field anymore.
            # otherwise IntegrityError will raise because text will be None
            if result.field in pkg_dict:
                pkg_processed_field.append(result.field)
                log.debug('::::::::::::::: value before %r', result.text)
                result.text = pkg_dict.get(result.field)
                log.debug('::::::::::::::: value after %r', result.text)
                result.save()

        # Check for missing localized fields in DB
        for field_name in PKG_LOCALIZED_FIELDS:
            if field_name not in pkg_processed_field:
                field_data = pkg_dict.get(field_name)
                log.debug(f'Adding localized field {field_name}::{lang}')
                if field_data:
                    PackageMultilang.persist({'id': pkg_id,
                                              'field': field_name,
                                              'text': field_data},
                                             lang)
    else:
        log.info(':::::::::::: Localised fields are missing in package_multilang table, persisting defaults using values in the table package :::::::::::::::')
        for field_name in PKG_LOCALIZED_FIELDS:
            log.debug(f'Storing localized field {field_name}::{lang}')
            field_data = pkg_dict.get(field_name)
            if field_data:
                PackageMultilang.persist({'id': pkg_id,
                                          'field': field_name,
                                          'text': field_data},
                                         lang)


def before_view_dataset(odict, lang):
    #  Localizing Datasets names and descriptions in search list
    #  Localizing Tags display names in Facet list

    tags = odict.get('tags')
    if tags and helpers.is_tag_loc_enabled():
        for tag in tags:
            localized_tag = TagMultilang.by_tag_id(tag.get('id'), lang)

            if localized_tag:
                tag['display_name'] = localized_tag.text

    #  Localizing package sub dict for the dataset read page
    q_results = PackageMultilang.get_for_package_id_and_lang(odict.get('id'), lang)

    if q_results:
        for result in q_results:
            if odict.get(result.field, None):
                odict[result.field] = result.text
            else:
                extras = odict.get('extras', None)
                if extras and len(extras) > 0:
                    for extra in extras:
                        extra_key = extra.get('key', None)
                        if extra_key and extra_key == result.field:
                            extra['value'] = result.text

            # if result.field == 'notes':
            #    odict['notes'] = result.text

    # Localizing organization sub dict for the dataset read page
    organization = odict.get('organization')
    if organization:
        q_results = GroupMultilang.get_for_group_id_and_lang(organization.get('id'), lang)

        if q_results:
            for result in q_results:
                organization[result.field] = result.text

        odict['organization'] = organization

    # Localizing resources dict
    resources = odict.get('resources')
    if resources:
        for resource in resources:
            q_results = ResourceMultilang.get_for_resource_id_and_lang(resource.get('id'), lang)

            if q_results:
                for result in q_results:
                    resource[result.field] = result.text

    return odict


def _localized_tags_persist(self, extra_tag, pkg_dict, lang):
    if extra_tag:
        for tag in extra_tag:
            localized_tag = TagMultilang.by_name(tag.get('key'), lang)

            if localized_tag and localized_tag.text != tag.get('value'):
                localized_tag.text = tag.get('value')
                localized_tag.save()
            elif localized_tag is None:
                # Find the tag id from the existing tags in dict
                tag_id = None
                for dict_tag in pkg_dict.get('tags'):
                    if dict_tag.get('name') == tag.get('key'):
                        tag_id = dict_tag.get('id')

                if tag_id:
                    TagMultilang.persist({'id': tag_id, 'name': tag.get('key'), 'text': tag.get('value')}, lang)