import logging
import operator

import ckan
import ckan.model as model
import ckan.plugins as p
import ckan.lib.search as search
import ckan.lib.helpers as h

import ckan.logic as logic

from pylons.i18n.translation import get_lang
from ckanext.multilang.model import PackageMultilang, GroupMultilang, TagMultilang, ResourceMultilang

log = logging.getLogger(__file__)

def get_localized_pkg(pkg_dict):
    if pkg_dict != '' and 'type' in pkg_dict:
        #  MULTILANG - Localizing package dict
        lang = get_lang()[0]

        #  MULTILANG - Localizing Tags display names in Facet list
        tags = pkg_dict['tags']
        for tag in tags:
            localized_tag = TagMultilang.by_tag_id(tag.get('id'), lang)

            if localized_tag:
                tag['display_name'] = localized_tag.text

        q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == pkg_dict.get('id'), PackageMultilang.lang == lang).all()

        if q_results:
            for result in q_results:
                pkg_dict[result.field] = result.text

        #  MULTILANG - Localizing organization sub dict for the dataset edit page
        organization = pkg_dict.get('organization')
        if organization:
            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == organization.get('id'), GroupMultilang.lang == lang).all() 

            if q_results:
                for result in q_results:
                    organization[result.field] = result.text

            pkg_dict['organization'] = organization

    return pkg_dict

def get_localized_group(org_dict):
    #  MULTILANG - Localizing group dict
    lang = get_lang()[0]
    
    q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == org_dict.get('id'), GroupMultilang.lang == lang).all()

    if q_results:
        for result in q_results:
            org_dict[result.field] = result.text
            if result.field == 'title':
                org_dict['display_name'] = result.text

    return org_dict

def get_localized_resource(resource_dict):
    #  MULTILANG - Localizing resource dict
    lang = get_lang()[0]

    q_results = model.Session.query(ResourceMultilang).filter(ResourceMultilang.resource_id == resource_dict.get('id'), ResourceMultilang.lang == lang).all()

    if q_results:
        for result in q_results:
            resource_dict[result.field] = result.text