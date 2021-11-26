import logging

import ckanext.multilang.helpers as helpers
from ckanext.multilang.model import PackageMultilang, TagMultilang, GroupMultilang, ResourceMultilang

log = logging.getLogger(__name__)


def after_create_dataset(context, package, lang):
    log.info(f'--> after_create_dataset {package}')


def after_update_dataset(context, package, lang):
    log.info(f'--> after_update_dataset {package}')


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
