import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.multilang.helpers as helpers

from routes.mapper import SubMapper, Mapper as _Mapper

log = logging.getLogger(__name__)


class MultilangPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IPackageController, inherit=True)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'multilang')

    # see the ITemplateHelpers plugin interface.
    def get_helpers(self):
        return {
            'get_localized_org': helpers.get_localized_org
        }

    def before_map(self, map):
        map.connect('/dataset', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='search')
        map.connect('/dataset/new', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='new')
        map.connect('/dataset/{id}', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='read')
        map.connect('/dataset/edit/{id}', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='edit')
        map.connect('/dataset/groups/{id}', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='groups')
        map.connect('/dataset/{id}/resource/{resource_id}', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='resource_read')
        map.connect('/dataset/{id}/resource_edit/{resource_id}', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='resource_edit')
        map.connect('/dataset/resources/{id}', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='resources')
        map.connect('/dataset/new_resource/{id}', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='new_resource')
        #map.connect('/dataset/{id}/resource_delete/{resource_id}', controller='ckanext.multilang.controllers.package:MultilangPackageController', action='resource_delete')

        map.connect('/group', controller='ckanext.multilang.controllers.group:MultilangGroupController', action='index')
        map.connect('/group/new', controller='ckanext.multilang.controllers.group:MultilangGroupController', action='new')
        map.connect('/group/{id}', controller='ckanext.multilang.controllers.group:MultilangGroupController', action='read')
        map.connect('/group/edit/{id}', controller='ckanext.multilang.controllers.group:MultilangGroupController', action='edit')
        map.connect('/group/about/{id}', controller='ckanext.multilang.controllers.group:MultilangGroupController', action='about')

        map.connect('/organization', controller='ckanext.multilang.controllers.organization:MultilangOrganizationController', action='index')
        map.connect('/organization/new', controller='ckanext.multilang.controllers.organization:MultilangOrganizationController', action='new')
        map.connect('/organization/{id}', controller='ckanext.multilang.controllers.organization:MultilangOrganizationController', action='read')
        map.connect('/organization/edit/{id}', controller='ckanext.multilang.controllers.organization:MultilangOrganizationController', action='edit')   
        map.connect('/organization/about/{id}', controller='ckanext.multilang.controllers.organization:MultilangOrganizationController', action='about')   

        map.connect('/user/{id:.*}', controller='ckanext.multilang.controllers.user:MultilangUserController', action='read') 

        return map

    def before_index(self, pkg_dict):
        from ckanext.multilang.model import PackageMultilang
        multilang_localized = PackageMultilang.get_for_package(pkg_dict['id'])

        for record in multilang_localized:
            log.debug('...Creating index for localized field: ' + record.field + ' - ' + record.lang)
            pkg_dict['multilang_localized_' + record.field + '_' + record.lang] = record.text
            log.debug('Index successfully created: %r', pkg_dict.get('multilang_localized_' + record.field + '_' + record.lang))

        return pkg_dict
        
    '''
    def before_search(self, search_params):
        log.debug('MULTILANG - search_params: %r', search_params)

        from pylons.i18n.translation import get_lang

        if get_lang():
            lang = get_lang()[0]

            #
            # Adding a localized query with the new created indexes into the
            # Solr facet queries.
            #
            fq = search_params.get('fq')
            log.debug('MULTILANG - fq: %r', fq)
            q = search_params.get('q')
            log.debug('MULTILANG - q: %r', q)
            
            if q and fq and q != '*:*':
                fq = fq + ' +(multilang_localized_title_' + lang + ':' + q + ' OR multilang_localized_notes_' + lang + ':' + q +')'
                search_params['fq'] = fq
                search_params['q'] = u''

            log.debug('::::::::::::::::::::::::::::::before_search - search_params: %r', search_params)

        return search_params
    '''    

