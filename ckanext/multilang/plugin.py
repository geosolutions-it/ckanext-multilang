import logging
from enum import Enum

from babel.core import Locale

from ckan.common import _
from ckan.lib import helpers as h
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.model as model
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.multilang.actions as actions
import ckanext.multilang.helpers as helpers
from ckanext.multilang.commands import cli
from ckanext.multilang.model import (
    GroupMultilang,
    PackageMultilang,
    ResourceMultilang,
    TagMultilang,
)
from ckanext.multilang.logic.package import (
    after_create_dataset,
    after_update_dataset,
    before_view_dataset,
)
from ckanext.multilang.logic.resource import (
    after_create_resource,
    after_update_resource,
    # before_view_resource,
)


class OBJ_TYPE(Enum):
    DATASET = 1
    RESOURCE = 2
    GROUP = 3
    ORG = 4
    HARVEST = 5


log = logging.getLogger(__name__)


def _find_obj_type(obj_dict):
    # Some heuristic to find out the object type

    otype = obj_dict.get('type')
    if otype == 'dataset':
        return OBJ_TYPE.DATASET
    if otype == 'harvest':
        return OBJ_TYPE.HARVEST
    if 'resource_type' in obj_dict:
        return OBJ_TYPE.RESOURCE

    raise Exception(f'Type unknown for {obj_dict}')


class MultilangPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):

    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IGroupController, inherit=True)
    plugins.implements(plugins.IOrganizationController, inherit=True)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IActions, inherit=True)

    def get_commands(self):
        return [
            cli.multilang
        ]

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'multilang')

    # see the ITemplateHelpers plugin interface.
    def get_helpers(self):
        return {
            'get_localized_pkg': helpers.get_localized_pkg,
            'get_localized_group': helpers.get_localized_group,
            'get_localized_resource': helpers.get_localized_resource,
            'is_tag_loc_enabled': helpers.is_tag_loc_enabled,
        }

    def get_actions(self):
        return {
            'group_list': actions.group_list,
            'organization_list': actions.organization_list
        }

    def before_index(self, pkg_dict):
        lang = helpers.getLanguage()
        pml_list = PackageMultilang.get_for_package(pkg_dict['id'])

        for ml_package in pml_list:
            # reading the values from the dict if possibile, since the DB may have not been updated yet
            if ml_package.field in pkg_dict and lang == ml_package.lang:
                value = pkg_dict[ml_package.field]
            else:
                value = ml_package.text

            log.debug(f'Creating index for package localized field: '
                      f'LANG:{ml_package.lang} FIELD:{ml_package.field} --> {value}')
            key = f'package_multilang_localized_{ml_package.field}_{ml_package.lang}'
            pkg_dict[key] = value

        return pkg_dict

    def before_view(self, odict):
        otype = odict.get('type')
        lang = helpers.getLanguage()

        log.debug(f'Dispatching before_view for TYPE:{otype} LANG:{lang}')

        if lang:
            if otype == 'group' or otype == 'organization':
                #  MULTILANG - Localizing Group/Organizzation names and descriptions in search list
                q_results = GroupMultilang.get_for_group_id_and_lang(odict.get('id'), lang)

                if q_results:
                    for result in q_results:
                        odict[result.field] = result.text
                        if result.field == 'title':
                            odict['display_name'] = result.text

            elif otype == 'dataset':
                odict = before_view_dataset(odict, lang)

        return odict

    def after_search(self, search_results, search_params):
        search_facets = search_results.get('search_facets')
        lang = helpers.getLanguage()

        if search_facets and lang:
            if 'tags' in search_facets:
                #  MULTILANG - Localizing Tags display names in Facet list
                tags = search_facets.get('tags')
                for tag in tags.get('items'):
                    localized_tag = TagMultilang.by_name(tag.get('name'), lang)

                    if localized_tag:
                        tag['display_name'] = localized_tag.text

            if 'organization' in search_facets:
                #  MULTILANG - Localizing Organizations display names in Facet list
                organizations = search_facets.get('organization')
                for org in organizations.get('items'):
                    # q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.name == org.get('name'), GroupMultilang.lang == lang).all()
                    q_results = GroupMultilang.get_for_group_name_and_lang(org.get('name'), lang)

                    if q_results:
                        for result in q_results:
                            if result.field == 'title':
                                org['display_name'] = result.text

            if 'groups' in search_facets:
                #  MULTILANG - Localizing Groups display names in Facet list
                groups = search_facets.get('groups')
                for group in groups.get('items'):
                    # q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.name == group.get('name'), GroupMultilang.lang == lang).all()
                    q_results = GroupMultilang.get_for_group_name_and_lang(group.get('name'), lang)

                    if q_results:
                        for result in q_results:
                            if result.field == 'title':
                                group['display_name'] = result.text

        search_results['search_facets'] = search_facets
        return search_results

    ## ##############
    # CREATE
    ## ##############
    def create(self, model_obj):
        otype = model_obj.type
        lang = helpers.getLanguage()
        log.debug(f'Dispatching create for TYPE:{otype} LANG:{lang}')

        # CREATE GROUP OR ORGANIZATION
        if otype in ('group', 'organization',) and lang:
            log.info(f'Storing multilang {lang} info for {otype} "{model_obj.name}"')
            lang = helpers.getLanguage()

            group_dict = {
                'id': model_obj.id,
                'name': model_obj.name,
                'title': model_obj.title,
                'description': model_obj.description,
            }

            GroupMultilang.persist(group_dict, lang)

    ## ##############
    # EDIT
    ## ##############
    def edit(self, model_obj):
        otype = model_obj.type
        lang = helpers.getLanguage()
        log.debug(f'Dispatching edit for TYPE:{otype} LANG:{lang}')

        # EDIT GROUP OR ORGANIZATION
        if otype == 'group' or otype == 'organization' and lang:
            group = model_dictize.group_dictize(model_obj, {'model': model, 'session': model.Session})

            # q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == group.get('id')).all()
            q_results = GroupMultilang.get_for_group_id(group.get('id'))

            create_new = False
            if q_results:
                available_db_lang = []

                for result in q_results:
                    if result.lang not in available_db_lang:
                        available_db_lang.append(result.lang)

                    # check if the group identifier name has been changed
                    if result.name != group.get('name'):
                        result.name = group.get('name')
                        result.save()

                if lang not in available_db_lang:
                    create_new = True
                else:
                    for result in q_results:
                        if result.lang == lang:
                            result.text = group.get(result.field)
                            result.save()
            else:
                create_new = True

            if create_new:
                log.info(':::::::::::: Localized fields are missing in package_multilang table, persisting defaults using values in the table group :::::::::::::::')
                GroupMultilang.persist(group, lang)

    ## ##############
    # DELETE
    ## ##############
    def delete(self, model_obj):
        return model_obj

    def before_show(self, resource_dict):
        lang = helpers.getLanguage()
        if lang:
            #  MULTILANG - Localizing resources dict
            q_results = ResourceMultilang.get_for_resource_id_and_lang(resource_dict.get('id'), lang)

            if q_results:
                for result in q_results:
                    resource_dict[result.field] = result.text

        return resource_dict

    def after_update(self, context, obj_dict):
        otype = _find_obj_type(obj_dict)
        lang = helpers.getLanguage()
        log.debug(f'Dispatching after_update for TYPE:{otype} LANG:{lang}')

        if lang:
            if otype == OBJ_TYPE.RESOURCE:
                after_update_resource(context, obj_dict, lang)
            elif otype == OBJ_TYPE.DATASET:
                after_update_dataset(context, obj_dict, lang)

    def after_create(self, context, obj_dict):
        otype = _find_obj_type(obj_dict)
        lang = helpers.getLanguage()
        log.debug(f'Dispatching after_create for TYPE:{otype} LANG:{lang}')

        if lang:
            if otype == OBJ_TYPE.RESOURCE:
                after_create_resource(context, obj_dict, lang)
            elif otype == OBJ_TYPE.DATASET:
                after_create_dataset(context, obj_dict, lang)


class MultilangResourcesPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):

    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.ITemplateHelpers)

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    def show_package_schema(self):
        schema = super(MultilangResourcesPlugin, self).show_package_schema()
        return MultilangResourcesAux().update_schema(schema)

    def create_package_schema(self):
        schema = super(MultilangResourcesPlugin, self).create_package_schema()
        return MultilangResourcesAux().update_schema(schema)

    def update_package_schema(self):
        schema = super(MultilangResourcesPlugin, self).update_package_schema()
        return MultilangResourcesAux().update_schema(schema)

    def read_template(self):
        return MultilangResourcesAux().read_template()

    def resource_form(self):
        return MultilangResourcesAux().resource_form()

    def get_helpers(self):
        return MultilangResourcesAux().get_helpers()


class MultilangResourcesAux():
    """
    IDatasetForm has some problems when inherited more than once,
    so this class exposes methods for being reused by external plugins that
    needs the multilang resources functionality.
    """

    def _get_lang_name(self, lang):
        loc = Locale(lang)
        return loc.display_name or loc.english_name

    def _format_resource_items(self, items):
        """
        this wraps default implementation and for fields from custom schema
        it applies localized labels and values if possible
        """
        out = h.format_resource_items(items)
        new_out = []
        for key, val in items:
            if key == 'lang' and val:
                key = _('Language')
                loc = Locale(val)
                val = '{} [{}]'.format(loc.display_name or loc.english_name, str(loc))
            new_out.append((key, val))
        return new_out

    def _get_resource_schema(self):
        return [{'name': 'lang',
                 'type': 'vocabulary',
                 'label': _('Language'),
                 'placeholder': _('Enter language code'),
                 'help': _('Set language for which this resource will be visible'),
                 'validators': ['ignore_missing']}]

    def update_schema(self, schema):
        fields = self._get_resource_schema()
        gv = toolkit.get_validator
        res_schema = dict((r['name'], [gv(v) for v in r['validators']]) for r in fields)

        res = schema['resources']
        res.update(res_schema)
        schema['resources'] = res
        return schema

    def read_template(self):
        return 'package/read_multilang.html'

    def resource_form(self):
        return 'package/snippets/resource_form_multilang.html'

    def get_helpers(self):
        multilang_helpers = {
            'get_multilang_resource_schema': self._get_resource_schema,
            'format_resource_items': self._format_resource_items,
            'get_lang_name': self._get_lang_name,
        }
        return multilang_helpers
