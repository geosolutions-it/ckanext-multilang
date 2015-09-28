import logging
from urllib import quote

from pylons import config

import ckan.lib.base as base
import ckan.model as model
import ckan.lib.helpers as h
import ckan.authz as authz
import ckan.logic as logic
import ckan.logic.schema as schema
import ckan.lib.captcha as captcha
import ckan.lib.mailer as mailer
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.lib.authenticator as authenticator
import ckan.plugins as p

from ckan.common import _, c, g, request, response

from pylons.i18n.translation import get_lang
from ckanext.multilang.model import PackageMultilang

from ckan.controllers.user import UserController

log = logging.getLogger(__name__)

abort = base.abort
render = base.render

check_access = logic.check_access
get_action = logic.get_action
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
UsernamePasswordError = logic.UsernamePasswordError

DataError = dictization_functions.DataError
unflatten = dictization_functions.unflatten

class MultilangUserController(UserController):
    '''
        Overrides the UserController in order to provide a localized 
        list of Datasets of the User 
    '''

    def _setup_template_variables(self, context, data_dict):
        c.is_sysadmin = authz.is_sysadmin(c.user)
        try:
            user_dict = get_action('user_show')(context, data_dict)
        except NotFound:
            abort(404, _('User not found'))
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        c.user_dict = user_dict

        lang = get_lang()[0]

        #  MULTILANG - Localizing Datasets names and descriptions in search list
        for item in c.user_dict.get('datasets'):
            log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')
            
            q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == item.get('id'), PackageMultilang.lang == lang).all() 

            if q_results:
                for result in q_results:
                    item[result.field] = result.text

        c.is_myself = user_dict['name'] == c.user
        c.about_formatted = h.render_markdown(user_dict['about'])
