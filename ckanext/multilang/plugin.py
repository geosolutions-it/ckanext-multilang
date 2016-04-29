import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.multilang.helpers as helpers
import ckanext.multilang.actions as actions

from routes.mapper import SubMapper, Mapper as _Mapper

log = logging.getLogger(__name__)


class MultilangPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IActions)

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
        
        # users
        map.redirect('/users/{url:.*}', '/user/{url}')
        map.redirect('/user/', '/user')
        with SubMapper(map, controller='user') as m:
            m.connect('/user/edit', action='edit')
            # Note: openid users have slashes in their ids, so need the wildcard
            # in the route.
            m.connect('user_generate_apikey', '/user/generate_key/{id}', action='generate_apikey')
            m.connect('/user/activity/{id}/{offset}', action='activity')
            m.connect('user_activity_stream', '/user/activity/{id}',
                      action='activity', ckan_icon='time')
            m.connect('user_dashboard', '/dashboard', action='dashboard',
                      ckan_icon='list')
            m.connect('user_dashboard_datasets', '/dashboard/datasets',
                      action='dashboard_datasets', ckan_icon='sitemap')
            m.connect('user_dashboard_groups', '/dashboard/groups',
                      action='dashboard_groups', ckan_icon='group')
            m.connect('user_dashboard_organizations', '/dashboard/organizations',
                      action='dashboard_organizations', ckan_icon='building')
            m.connect('/dashboard/{offset}', action='dashboard')
            m.connect('user_follow', '/user/follow/{id}', action='follow')
            m.connect('/user/unfollow/{id}', action='unfollow')
            m.connect('user_followers', '/user/followers/{id:.*}',
                      action='followers', ckan_icon='group')
            m.connect('user_edit', '/user/edit/{id:.*}', action='edit',
                      ckan_icon='cog')
            m.connect('user_delete', '/user/delete/{id}', action='delete')
            m.connect('/user/reset/{id:.*}', action='perform_reset')
            m.connect('register', '/user/register', action='register')
            m.connect('login', '/user/login', action='login')
            m.connect('/user/_logout', action='logout')
            m.connect('/user/logged_in', action='logged_in')
            m.connect('/user/logged_out', action='logged_out')
            m.connect('/user/logged_out_redirect', action='logged_out_page')
            m.connect('/user/reset', action='request_reset')
            m.connect('/user/me', action='me')
            m.connect('/user/set_lang/{lang}', action='set_lang')
            #m.connect('user_datasets', '/user/{id:.*}', action='read',
            #          ckan_icon='sitemap')
            m.connect('user_index', '/user', action='index')
        
            map.connect('/user/{id:.*}', controller='ckanext.multilang.controllers.user:MultilangUserController', action='read') 

        return map

    def before_index(self, pkg_dict):
        from ckanext.multilang.model import PackageMultilang
        multilang_localized = PackageMultilang.get_for_package(pkg_dict['id'])

        for package in multilang_localized:
            log.debug('...Creating index for Package localized field: ' + package.field + ' - ' + package.lang)
            pkg_dict['package_multilang_localized_' + package.field + '_' + package.lang] = package.text
            log.debug('Index successfully created for Package: %r', pkg_dict.get('package_multilang_localized_' + package.field + '_' + package.lang))

        '''from ckanext.multilang.model import GroupMultilang
        multilang_localized = GroupMultilang.get_for_group_name(str(pkg_dict['organization']))

        for organization in multilang_localized:
            log.debug('...Creating index for Organization localized field: ' + organization.field + ' - ' + organization.lang)
            pkg_dict['organization_multilang_localized_' + organization.field + '_' + organization.lang] = organization.text
            log.debug('Index successfully created for Organization: %r', pkg_dict.get('organization_multilang_localized_' + organization.field + '_' + organization.lang))

        for group in pkg_dict['groups']:
            multilang_localized = GroupMultilang.get_for_group_name(str(group))

            for record in multilang_localized:
                log.debug('...Creating index for Group localized field: ' + organization.field + ' - ' + organization.lang)
                pkg_dict['group_multilang_localized_' + record.field + '_' + record.lang] = record.text
                log.debug('Index successfully created for Group: %r', pkg_dict.get('group_multilang_localized_' + organization.field + '_' + organization.lang))'''

        return pkg_dict

    def get_actions(self):
        return {
            'group_list': actions.group_list,
            'organization_list': actions.organization_list
        }
        
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

