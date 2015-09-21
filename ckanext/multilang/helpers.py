import logging
import operator

import ckan
import ckan.model as model
import ckan.plugins as p
import ckan.lib.search as search
import ckan.lib.helpers as h

import ckan.logic as logic

from pylons.i18n.translation import get_lang
from ckanext.multilang.model import GroupMultilang

log = logging.getLogger(__file__)

def get_localized_org(org_id):
    #
    # Return the localized organization conresponding to the provided id
    #
    lang = get_lang()[0]
    q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == org_id, GroupMultilang.lang == lang).all() 

    display_name = None
    if q_results:
        for result in q_results:
            if result.field == 'title':
                display_name = result.text

    return display_name
