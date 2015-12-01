import logging
import cgi

import ckan 

import ckan.logic as logic
import ckan.lib.base as base
import ckan.plugins as p
import ckan.lib.maintain as maintain

from pylons import config

from pylons.i18n.translation import get_lang

from urllib import urlencode
from paste.deploy.converters import asbool
from ckan.lib.base import request
from ckan.lib.base import c, g, h
from ckan.lib.base import model
from ckan.lib.base import render
from ckan.lib.base import _

import ckan.lib.navl.dictization_functions as dict_fns

from ckan.lib.navl.validators import not_empty

from ckan.common import OrderedDict, _, json, request, c, g, response

from ckan.controllers.package import PackageController
from ckanext.multilang.model import PackageMultilang, GroupMultilang, ResourceMultilang, TagMultilang

from ckan.controllers.home import CACHE_PARAMETERS

log = logging.getLogger(__name__)

render = base.render
abort = base.abort
redirect = base.redirect

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
get_action = logic.get_action
check_access = logic.check_access
clean_dict = logic.clean_dict
tuplize_dict = logic.tuplize_dict
parse_params = logic.parse_params

def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v))
            for k, v in params]

def url_with_params(url, params):
    params = _encode_params(params)
    return url + u'?' + urlencode(params)

def search_url(params, package_type=None):
    if not package_type or package_type == 'dataset':
        url = h.url_for(controller='package', action='search')
    else:
        url = h.url_for('{0}_search'.format(package_type))
    return url_with_params(url, params)

class MultilangPackageController(PackageController):

    ## Managed localized fields for Package in package_multilang table
    pkg_localized_fields = [
        'title',
        'notes',
        'author',
        'maintainer',
        'url'
    ]

    """
       This controller overrides the core PackageController 
       for dataset list view search and dataset details page
    """

    def search(self):
        from ckan.lib.search import SearchError

        package_type = self._guess_package_type()

        try:
            context = {'model': model, 'user': c.user or c.author,
                       'auth_user_obj': c.userobj}
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        # unicode format (decoded from utf8)
        q = c.q = request.params.get('q', u'')
        c.query_error = False
        page = self._get_page_number(request.params)

        limit = g.datasets_per_page

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']

        def drill_down_url(alternative_url=None, **by):
            return h.add_url_param(alternative_url=alternative_url,
                                   controller='package', action='search',
                                   new_params=by)

        c.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            return h.remove_url_param(key, value=value, replace=replace,
                                  controller='package', action='search')

        c.remove_field = remove_field

        sort_by = request.params.get('sort', None)
        params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

        def _sort_by(fields):
            """
            Sort by the given list of fields.

            Each entry in the list is a 2-tuple: (fieldname, sort_order)

            eg - [('metadata_modified', 'desc'), ('name', 'asc')]

            If fields is empty, then the default ordering is used.
            """
            params = params_nosort[:]

            if fields:
                sort_string = ', '.join('%s %s' % f for f in fields)
                params.append(('sort', sort_string))
            return search_url(params, package_type)

        c.sort_by = _sort_by
        if not sort_by:
            c.sort_by_fields = []
        else:
            c.sort_by_fields = [field.split()[0]
                                for field in sort_by.split(',')]

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params, package_type)

        c.search_url_params = urlencode(_encode_params(params_nopage))

        try:
            c.fields = []
            # c.fields_grouped will contain a dict of params containing
            # a list of values eg {'tags':['tag1', 'tag2']}
            c.fields_grouped = {}
            search_extras = {}
            fq = ''
            for (param, value) in request.params.items():
                if param not in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        fq += ' %s:"%s"' % (param, value)
                        if param not in c.fields_grouped:
                            c.fields_grouped[param] = [value]
                        else:
                            c.fields_grouped[param].append(value)
                    else:
                        search_extras[param] = value

            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author, 'for_view': True,
                       'auth_user_obj': c.userobj}

            if package_type and package_type != 'dataset':
                # Only show datasets of this particular type
                fq += ' +dataset_type:{type}'.format(type=package_type)
            else:
                # Unless changed via config options, don't show non standard
                # dataset types on the default search page
                if not asbool(config.get('ckan.search.show_all_types', 'False')):
                    fq += ' +dataset_type:dataset'

            facets = OrderedDict()

            default_facet_titles = {
                    'organization': _('Organizations'),
                    'groups': _('Groups'),
                    'tags': _('Tags'),
                    'res_format': _('Formats'),
                    'license_id': _('Licenses'),
                    }

            for facet in g.facets:
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            for plugin in p.PluginImplementations(p.IFacets):
                facets = plugin.dataset_facets(facets, package_type)

            c.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': fq.strip(),
                'facet.field': facets.keys(),
                'rows': limit,
                'start': (page - 1) * limit,
                'sort': sort_by,
                'extras': search_extras
            }

            query = get_action('package_search')(context, data_dict)
            c.sort_by_selected = query['sort']

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )
            c.facets = query['facets']
            c.search_facets = query['search_facets']

            lang = get_lang()[0]
            
            #  MULTILANG - Localizing Tags display names in Facet list
            tags = c.search_facets.get('tags')
            for tag in tags.get('items'):
                localized_tag = TagMultilang.by_name(tag.get('name'), lang)

                if localized_tag:
                    tag['display_name'] = localized_tag.text
            
            #  MULTILANG - Localizing Organizations display names in Facet list
            organizations = c.search_facets.get('organization')

            for org in organizations.get('items'):
                q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.name == org.get('name'), GroupMultilang.lang == lang).all() 

                if q_results:
                    for result in q_results:
                        if result.field == 'title':
                            org['display_name'] = result.text

            #  MULTILANG - Localizing Groups display names in Facet list
            groups = c.search_facets.get('groups')
            for group in groups.get('items'):
                q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.name == group.get('name'), GroupMultilang.lang == lang).all() 

                if q_results:
                    for result in q_results:
                        if result.field == 'title':
                            group['display_name'] = result.text

            c.page.items = query['results']

            #  MULTILANG - Localizing Datasets names and descriptions in search list
            for item in c.page.items:
                log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')
                
                q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == item.get('id'), PackageMultilang.lang == lang).all() 

                if q_results:
                    for result in q_results:
                        item[result.field] = result.text
                
        except SearchError, se:
            log.error('Dataset search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.search_facets = {}
            c.page = h.Page(collection=[])
        c.search_facets_limits = {}
        for facet in c.search_facets.keys():
            try:
                limit = int(request.params.get('_%s_limit' % facet,
                                               g.facets_default_number))
            except ValueError:
                abort(400, _('Parameter "{parameter_name}" is not '
                             'an integer').format(
                                 parameter_name='_%s_limit' % facet
                             ))
            c.search_facets_limits[facet] = limit

        maintain.deprecate_context_item(
          'facets',
          'Use `c.search_facets` instead.')

        self._setup_template_variables(context, {},
                                       package_type=package_type)

        return render(self._search_template(package_type),
                      extra_vars={'dataset_type': package_type})

    def read(self, id, format='html'):
        if not format == 'html':
            ctype, extension = \
                self._content_type_from_extension(format)
            if not ctype:
                # An unknown format, we'll carry on in case it is a
                # revision specifier and re-constitute the original id
                id = "%s.%s" % (id, format)
                ctype, format = "text/html; charset=utf-8", "html"
        else:
            ctype, format = self._content_type_from_accept()

        response.headers['Content-Type'] = ctype

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id, 'include_tracking': True}

        # interpret @<revision_id> or @<date> suffix
        split = id.split('@')
        if len(split) == 2:
            data_dict['id'], revision_ref = split
            if model.is_id(revision_ref):
                context['revision_id'] = revision_ref
            else:
                try:
                    date = h.date_str_to_datetime(revision_ref)
                    context['revision_date'] = date
                except TypeError, e:
                    abort(400, _('Invalid revision format: %r') % e.args)
                except ValueError, e:
                    abort(400, _('Invalid revision format: %r') % e.args)
        elif len(split) > 2:
            abort(400, _('Invalid revision format: %r') %
                  'Too many "@" symbols')

        # check if package exists
        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            c.pkg = context['package']
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)

        # used by disqus plugin
        c.current_package_id = c.pkg.id
        c.related_count = c.pkg.related_count

        # can the resources be previewed?
        for resource in c.pkg_dict['resources']:
            # Backwards compatibility with preview interface
            resource['can_be_previewed'] = self._resource_preview(
                {'resource': resource, 'package': c.pkg_dict})

            resource_views = get_action('resource_view_list')(
                context, {'id': resource['id']})
            resource['has_views'] = len(resource_views) > 0

        package_type = c.pkg_dict['type'] or 'dataset'

        log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')

        lang = get_lang()[0]        

        #  MULTILANG - Localizing Tags display names in Facet list
        tags = c.pkg_dict['tags']
        for tag in tags:
            localized_tag = TagMultilang.by_tag_id(tag.get('id'), lang)

            if localized_tag:
                tag['display_name'] = localized_tag.text

        #  MULTILANG - Localizing package sub dict for the dataset read page
        q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == c.pkg_dict['id'], PackageMultilang.lang == lang).all() 

        if q_results:
            for result in q_results:
                c.pkg_dict[result.field] = result.text
                if result.field == 'notes':
                    c.pkg.notes = result.text

        #  MULTILANG - Localizing organization sub dict for the dataset read page
        organization = c.pkg_dict.get('organization')
        if organization:
            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == organization.get('id'), GroupMultilang.lang == lang).all() 
            
            if q_results:
                for result in q_results:
                    organization[result.field] = result.text

            c.pkg_dict['organization'] = organization

        #  MULTILANG - Localizing resources dict
        resources = c.pkg_dict.get('resources')
        if resources:
            for resource in resources:
                q_results = model.Session.query(ResourceMultilang).filter(ResourceMultilang.resource_id == resource.get('id'), ResourceMultilang.lang == lang).all()
        
                if q_results:
                    for result in q_results:
                        resource[result.field] = result.text
        
        self._setup_template_variables(context, {'id': id},
                                       package_type=package_type)

        template = self._read_template(package_type)
        template = template[:template.index('.') + 1] + format
        
        try:
            return render(template,
                          extra_vars={'dataset_type': package_type})
        except ckan.lib.render.TemplateNotFound:
            msg = _("Viewing {package_type} datasets in {format} format is "
                    "not supported (template file {file} not found).".format(
                    package_type=package_type, format=format, file=template))
            abort(404, msg)

        assert False, "We should never get here"

    def edit(self, id, data=None, errors=None, error_summary=None):
        package_type = self._get_package_type(id)
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'save': 'save' in request.params}

        if context['save'] and not data:
            return self._save_edit(id, context, package_type=package_type)
        try:
            c.pkg_dict = get_action('package_show')(context, {'id': id})
            context['for_edit'] = True
            old_data = get_action('package_show')(context, {'id': id})
            # old data is from the database and data is passed from the
            # user if there is a validation error. Use users data if there.
            if data:
                old_data.update(data)
            data = old_data
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound:
            abort(404, _('Dataset not found'))
        # are we doing a multiphase add?
        if data.get('state', '').startswith('draft'):
            c.form_action = h.url_for(controller='package', action='new')
            c.form_style = 'new'
            return self.new(data=data, errors=errors,
                            error_summary=error_summary)

        c.pkg = context.get("package")

        #  MULTILANG - Localizing package dict 
        log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')

        lang = get_lang()[0]

        #  MULTILANG - Localizing Tags display names in Facet list
        tags = data['tags']
        for tag in tags:
            localized_tag = TagMultilang.by_tag_id(tag.get('id'), lang)

            if localized_tag:
                tag['display_name'] = localized_tag.text

        q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == data.get('id'), PackageMultilang.lang == lang).all()

        if q_results:
            for result in q_results:
                data[result.field] = result.text
                c.pkg_dict[result.field] = result.text

        #  MULTILANG - Localizing organization sub dict for the dataset edit page
        organization = c.pkg_dict.get('organization')
        if organization:
            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == organization.get('id'), GroupMultilang.lang == lang).all() 

            if q_results:
                for result in q_results:
                    organization[result.field] = result.text

            c.pkg_dict['organization'] = organization

        c.resources_json = h.json.dumps(data.get('resources', []))

        try:
            check_access('package_update', context)
        except NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))
        # convert tags if not supplied in data
        if data and not data.get('tag_string'):
            data['tag_string'] = ', '.join(h.dict_list_reduce(
                c.pkg_dict.get('tags', {}), 'name'))
        errors = errors or {}
        form_snippet = self._package_form(package_type=package_type)
        form_vars = {'data': data, 'errors': errors,
                     'error_summary': error_summary, 'action': 'edit',
                     'dataset_type': package_type,
                    }
        c.errors_json = h.json.dumps(errors)

        self._setup_template_variables(context, {'id': id},
                                       package_type=package_type)
        c.related_count = c.pkg.related_count

        # we have already completed stage 1
        form_vars['stage'] = ['active']
        if data.get('state', '').startswith('draft'):
            form_vars['stage'] = ['active', 'complete']

        edit_template = self._edit_template(package_type)
        c.form = ckan.lib.render.deprecated_lazy_render(
            edit_template,
            form_snippet,
            lambda: render(form_snippet, extra_vars=form_vars),
            'use of c.form is deprecated. please see '
            'ckan/templates/package/edit.html for an example '
            'of the new way to include the form snippet'
            )
        return render(edit_template,
                      extra_vars={'form_vars': form_vars,
                                  'form_snippet': form_snippet,
                                  'dataset_type': package_type})

    def localized_tags_persist(self, extra_tag, pkg_dict, lang):
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
                        session = model.Session
                        try:
                            session.add_all([
                                TagMultilang(tag_id=tag_id, tag_name=tag.get('key'), lang=lang, text=tag.get('value')),
                            ])

                            session.commit()
                        except Exception, e:
                            # on rollback, the same closure of state
                            # as that of commit proceeds. 
                            session.rollback()

                            log.error('Exception occurred while persisting DB objects: %s', e)
                            raise

    def _save_new(self, context, package_type=None):
        # The staged add dataset used the new functionality when the dataset is
        # partially created so we need to know if we actually are updating or
        # this is a real new.
        is_an_update = False
        ckan_phase = request.params.get('_ckan_phase')
        from ckan.lib.search import SearchIndexError
        try:
            data_dict = clean_dict(dict_fns.unflatten(
                tuplize_dict(parse_params(request.POST))))
            if ckan_phase:
                # prevent clearing of groups etc
                context['allow_partial_update'] = True
                # sort the tags
                if 'tag_string' in data_dict:
                    data_dict['tags'] = self._tag_string_to_list(
                        data_dict['tag_string'])
                if data_dict.get('pkg_name'):
                    is_an_update = True
                    # This is actually an update not a save
                    data_dict['id'] = data_dict['pkg_name']
                    del data_dict['pkg_name']
                    # don't change the dataset state
                    data_dict['state'] = 'draft'
                    # this is actually an edit not a save
                    pkg_dict = get_action('package_update')(context, data_dict)

                    if request.params['save'] == 'go-metadata':
                        # redirect to add metadata
                        url = h.url_for(controller='package',
                                        action='new_metadata',
                                        id=pkg_dict['name'])
                    else:
                        # redirect to add dataset resources
                        url = h.url_for(controller='package',
                                        action='new_resource',
                                        id=pkg_dict['name'])
                    redirect(url)
                # Make sure we don't index this dataset
                if request.params['save'] not in ['go-resource', 'go-metadata']:
                    data_dict['state'] = 'draft'
                # allow the state to be changed
                context['allow_state_change'] = True

            data_dict['type'] = package_type
            context['message'] = data_dict.get('log_message', '')

            #  MULTILANG - retrieving dict for localized tag's strings
            extra_tag = None
            if data_dict.get('extra_tag'):
                extra_tag = data_dict.get('extra_tag')
                # After saving in memory the extra_tag dict this must be removed because not present in the schema
                del data_dict['extra_tag']

            pkg_dict = get_action('package_create')(context, data_dict)

            lang = get_lang()[0]

            #  MULTILANG - persisting tags
            self.localized_tags_persist(extra_tag, pkg_dict, lang)

            # MULTILANG - persisting the localized package dict
            log.info('::::: Persisting localised metadata locale :::::')
            pkg_to_persist = []
            for field in self.pkg_localized_fields and pkg_dict.get(field):
                pkg_to_persist.append(PackageMultilang(package_id=pkg_dict.get('id'), field=field, field_type='localized', lang=lang, text=pkg_dict.get(field)))
            
            if len(pkg_to_persist) > 0:
                self.persistPackageMultilangs(pkg_to_persist)

            if ckan_phase:
                # redirect to add dataset resources
                url = h.url_for(controller='package',
                                action='new_resource',
                                id=pkg_dict['name'])
                redirect(url)

            self._form_save_redirect(pkg_dict['name'], 'new', package_type=package_type)
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound, e:
            abort(404, _('Dataset not found'))
        except dict_fns.DataError:
            abort(400, _(u'Integrity Error'))
        except SearchIndexError, e:
            try:
                exc_str = unicode(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = unicode(str(e))
            abort(500, _(u'Unable to add package to search index.') + exc_str)
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            if is_an_update:
                # we need to get the state of the dataset to show the stage we
                # are on.
                pkg_dict = get_action('package_show')(context, data_dict)
                data_dict['state'] = pkg_dict['state']
                return self.edit(data_dict['id'], data_dict,
                                 errors, error_summary)
            data_dict['state'] = 'none'
            return self.new(data_dict, errors, error_summary)

    def _save_edit(self, name_or_id, context, package_type=None):        
        from ckan.lib.search import SearchIndexError
        log.debug('Package save request name: %s POST: %r',
                  name_or_id, request.POST)
        try:
            data_dict = clean_dict(dict_fns.unflatten(
                tuplize_dict(parse_params(request.POST))))
            if '_ckan_phase' in data_dict:
                # we allow partial updates to not destroy existing resources
                context['allow_partial_update'] = True
                if 'tag_string' in data_dict:
                    data_dict['tags'] = self._tag_string_to_list(
                        data_dict['tag_string'])
                del data_dict['_ckan_phase']
                del data_dict['save']
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = name_or_id

            #  MULTILANG - retrieving dict for localized tag's strings
            extra_tag = None
            if data_dict.get('extra_tag'):
                extra_tag = data_dict.get('extra_tag')
                # After saving in memory the extra_tag dict this must be removed because not present in the schema
                del data_dict['extra_tag']

            pkg = get_action('package_update')(context, data_dict)
            
            c.pkg = context['package']
            c.pkg_dict = pkg

            lang = get_lang()[0]

            #  MULTILANG - persisting tags
            self.localized_tags_persist(extra_tag, c.pkg_dict, lang)

            #  MULTILANG - persisting package dict
            log.info(':::::::::::: Saving the corresponding localized title and abstract :::::::::::::::')
            
            q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == c.pkg_dict.get('id'), PackageMultilang.lang == lang).all()
            
            if q_results:
                pkg_processed_field = []
                for result in q_results:
                    pkg_processed_field.append(result.field)
                    log.debug('::::::::::::::: value before %r', result.text)
                    result.text = c.pkg_dict.get(result.field)
                    log.debug('::::::::::::::: value after %r', result.text)
                    result.save()

                ## Check for missing localized fields in DB
                obj_to_persist = []
                for field in self.pkg_localized_fields:
                    if field not in pkg_processed_field and c.pkg_dict.get(field):
                        obj_to_persist.append(PackageMultilang(package_id=c.pkg_dict.get('id'), field=field, field_type='localized', lang=lang, text=c.pkg_dict.get(field)))

                if len(obj_to_persist) > 0:
                    self.persistPackageMultilangs(obj_to_persist)

            else:
                log.info(':::::::::::: Localised fields are missing in package_multilang table, persisting defaults using values in the table package :::::::::::::::')
                pkg_to_persist = []
                for field in self.pkg_localized_fields and c.pkg_dict.get(field):
                    pkg_to_persist.append(PackageMultilang(package_id=c.pkg_dict.get('id'), field=field, field_type='localized', lang=lang, text=c.pkg_dict.get(field)))
                
                if len(pkg_to_persist) > 0:
                    self.persistPackageMultilangs(pkg_to_persist)

            self._form_save_redirect(pkg['name'], 'edit', package_type=package_type)
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)
        except NotFound, e:
            abort(404, _('Dataset not found'))
        except dict_fns.DataError:
            abort(400, _(u'Integrity Error'))
        except SearchIndexError, e:
            try:
                exc_str = unicode(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = unicode(str(e))
            abort(500, _(u'Unable to update search index.') + exc_str)
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(name_or_id, data_dict, errors, error_summary)

    def persistPackageMultilangs(self, pkg_list):
        if len(pkg_list) > 0:
            session = model.Session
            try:
                session.add_all(pkg_list)
                session.commit()
            except Exception, e:
                # on rollback, the same closure of state
                # as that of commit proceeds. 
                session.rollback()

                log.error('Exception occurred while persisting DB objects: %s', e)
                raise

    def groups(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'auth_user_obj': c.userobj, 'use_cache': False}
        data_dict = {'id': id}
        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            dataset_type = c.pkg_dict['type'] or 'dataset'
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read dataset %s') % id)

        if request.method == 'POST':
            new_group = request.POST.get('group_added')
            if new_group:
                data_dict = {"id": new_group,
                             "object": id,
                             "object_type": 'package',
                             "capacity": 'public'}
                try:
                    get_action('member_create')(context, data_dict)
                except NotFound:
                    abort(404, _('Group not found'))

            removed_group = None
            for param in request.POST:
                if param.startswith('group_remove'):
                    removed_group = param.split('.')[-1]
                    break
            if removed_group:
                data_dict = {"id": removed_group,
                             "object": id,
                             "object_type": 'package'}

                try:
                    get_action('member_delete')(context, data_dict)
                except NotFound:
                    abort(404, _('Group not found'))
            redirect(h.url_for(controller='package',
                               action='groups', id=id))

        #  MULTILANG - Localizing package dict
        log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')

        lang = get_lang()[0]

        q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == c.pkg_dict['id'], PackageMultilang.lang == lang).all() 

        if q_results:
            for result in q_results:
                c.pkg_dict[result.field] = result.text
        
        #  MULTILANG - Localizing Organizations names in breadcrumb
        organization = c.pkg_dict.get('organization')

        q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.name == organization.get('name'), GroupMultilang.lang == lang).all() 

        if q_results:
            for result in q_results:
                    organization[result.field] = result.text

        #  MULTILANG - Localizing Groups names and description in groups list
        groups = c.pkg_dict.get('groups')
        for group in groups:
            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.name == group.get('name'), GroupMultilang.lang == lang).all() 

            if q_results:
                for result in q_results:
                    group[result.field] = result.text
                    if result.field == 'title':
                        group['display_name'] = result.text

        context['is_member'] = True
        users_groups = get_action('group_list_authz')(context, data_dict)

        pkg_group_ids = set(group['id'] for group
                         in c.pkg_dict.get('groups', []))
        user_group_ids = set(group['id'] for group
                          in users_groups)

        c.group_dropdown = [[group['id'], group['display_name']]
                           for group in users_groups if
                           group['id'] not in pkg_group_ids]

        # Localizing Groups display names in dropdown list
        for group in c.group_dropdown:
            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == group[0], GroupMultilang.lang == lang).all() 

            if q_results:
                for result in q_results:
                    if result.field == 'title':
                        group[1] = result.text

        for group in c.pkg_dict.get('groups', []):
            group['user_member'] = (group['id'] in user_group_ids)

        return render('package/group_list.html',
                      {'dataset_type': dataset_type})

    def resource_read(self, id, resource_id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj, "for_view":True}

        try:
            c.package = get_action('package_show')(context, {'id': id})
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read dataset %s') % id)

        for resource in c.package.get('resources', []):
            if resource['id'] == resource_id:
                c.resource = resource
                break
        if not c.resource:
            abort(404, _('Resource not found'))

        # required for nav menu
        c.pkg = context['package']
        c.pkg_dict = c.package
        dataset_type = c.pkg.type or 'dataset'

        #  MULTILANG - locaizing package dict
        log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')

        lang = get_lang()[0]        

        q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == c.pkg_dict['id'], PackageMultilang.lang == lang).all() 

        if q_results:
            for result in q_results:
                c.pkg_dict[result.field] = result.text
                c.pkg.notes = result.text

        # MULTILANG - Localizing organization sub dict for the dataset read page
        organization = c.pkg_dict.get('organization')
        if organization:
            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == organization.get('id'), GroupMultilang.lang == lang).all() 
            
            if q_results:
                for result in q_results:
                    organization[result.field] = result.text

            c.pkg_dict['organization'] = organization

        # get package license info
        license_id = c.package.get('license_id')
        try:
            c.package['isopen'] = model.Package.\
                get_license_register()[license_id].isopen()
        except KeyError:
            c.package['isopen'] = False

        # TODO: find a nicer way of doing this
        c.datastore_api = '%s/api/action' % config.get('ckan.site_url', '').rstrip('/')

        c.related_count = c.pkg.related_count

        c.resource['can_be_previewed'] = self._resource_preview(
            {'resource': c.resource, 'package': c.package})

        # MULTILANG - Localizing resource dict
        resources = c.pkg_dict.get('resources')
        if resources:
            for resource in resources:                
                q_results = model.Session.query(ResourceMultilang).filter(ResourceMultilang.resource_id == resource.get('id'), ResourceMultilang.lang == lang).all()
                if q_results:
                    for result in q_results:
                        resource[result.field] = result.text
                c.pkg_dict['resources'] = resources

        resource_views = get_action('resource_view_list')(
            context, {'id': resource_id})
        c.resource['has_views'] = len(resource_views) > 0

        current_resource_view = None
        view_id = request.GET.get('view_id')
        if c.resource['can_be_previewed'] and not view_id:
            current_resource_view = None
        elif c.resource['has_views']:
            if view_id:
                current_resource_view = [rv for rv in resource_views
                                         if rv['id'] == view_id]
                if len(current_resource_view) == 1:
                    current_resource_view = current_resource_view[0]
                else:
                    abort(404, _('Resource view not found'))
            else:
                current_resource_view = resource_views[0]

        vars = {'resource_views': resource_views,
                'current_resource_view': current_resource_view,
                'dataset_type': dataset_type}

        template = self._resource_template(dataset_type)
        return render(template, extra_vars=vars)

    def resource_edit(self, id, resource_id, data=None, errors=None,
                      error_summary=None):
        lang = get_lang()[0] 
        
        if request.method == 'POST' and not data:
            data = data or clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(
                request.POST))))
            # we don't want to include save as it is part of the form
            del data['save']

            context = {'model': model, 'session': model.Session,
                       'api_version': 3, 'for_edit': True,
                       'user': c.user or c.author, 'auth_user_obj': c.userobj}

            data['package_id'] = id

            #  MULTILANG - persisting resource localized record in multilang table
            q_results = model.Session.query(ResourceMultilang).filter(ResourceMultilang.resource_id == data.get('id'), ResourceMultilang.lang == lang).all()
            if q_results:
                for result in q_results:
                    result.text = data.get(result.field)
                    result.save()
            else:
                log.info('Localised fields are missing in resource_multilang table, persisting ...')
                session = model.Session
                try:
                    session.add_all([
                        ResourceMultilang(resource_id=data.get('id'), field='name', lang=lang, text=data.get('name')),
                        ResourceMultilang(resource_id=data.get('id'), field='description', lang=lang, text=data.get('description')),
                    ])

                    session.commit()
                except Exception, e:
                    # on rollback, the same closure of state
                    # as that of commit proceeds. 
                    session.rollback()

                    log.error('Exception occurred while persisting DB objects: %s', e)
                    raise

            try:
                if resource_id:
                    data['id'] = resource_id
                    get_action('resource_update')(context, data)
                else:
                    get_action('resource_create')(context, data)
            except ValidationError, e:
                errors = e.error_dict
                error_summary = e.error_summary
                return self.resource_edit(id, resource_id, data,
                                          errors, error_summary)
            except NotAuthorized:
                abort(401, _('Unauthorized to edit this resource'))
            redirect(h.url_for(controller='package', action='resource_read',
                               id=id, resource_id=resource_id))

        context = {'model': model, 'session': model.Session,
                   'api_version': 3, 'for_edit': True,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj}
        pkg_dict = get_action('package_show')(context, {'id': id})
        if pkg_dict['state'].startswith('draft'):
            # dataset has not yet been fully created
            resource_dict = get_action('resource_show')(context, {'id': resource_id})
            fields = ['url', 'resource_type', 'format', 'name', 'description', 'id']
            data = {}
            for field in fields:
                data[field] = resource_dict[field]
            return self.new_resource(id, data=data)
        # resource is fully created
        try:
            resource_dict = get_action('resource_show')(context, {'id': resource_id})
        except NotFound:
            abort(404, _('Resource not found'))

        c.pkg_dict = pkg_dict

        log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')

        q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == c.pkg_dict['id'], PackageMultilang.lang == lang).all() 

        if q_results:
            for result in q_results:
                c.pkg_dict[result.field] = result.text

        #  MULTILANG - Localizing organization sub dict 
        organization = c.pkg_dict.get('organization')
        if organization:
            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == organization.get('id'), GroupMultilang.lang == lang).all() 
            
            if q_results:
                for result in q_results:
                    organization[result.field] = result.text

            c.pkg_dict['organization'] = organization
       
        c.resource = resource_dict

        #  MULTILANG - Localizing resources dict
        q_results = model.Session.query(ResourceMultilang).filter(ResourceMultilang.resource_id == c.resource.get('id'), ResourceMultilang.lang == lang).all()

        if q_results:
            for result in q_results:
                c.resource[result.field] = result.text

        # set the form action
        c.form_action = h.url_for(controller='package',
                                  action='resource_edit',
                                  resource_id=resource_id,
                                  id=id)
        if not data:
            data = resource_dict

        package_type = pkg_dict['type'] or 'dataset'

        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary, 'action': 'new',
                'resource_form_snippet': self._resource_form(package_type),
                'dataset_type':package_type}
        return render('package/resource_edit.html', extra_vars=vars)

    def resources(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id, 'include_tracking': True}

        try:
            check_access('package_update', context, data_dict)
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))
        # check if package exists
        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            c.pkg = context['package']

            log.info(':::::::::::: Retrieving the corresponding localized fields for the page of resources :::::::::::::::')
            lang = get_lang()[0] 

            #  MULTILANG -Localizing package fields
            q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == c.pkg_dict['id'], PackageMultilang.lang == lang).all() 

            if q_results:
                for result in q_results:
                    c.pkg_dict[result.field] = result.text

            #  MULTILANG -Localizing resources dict
            resources = c.pkg_dict.get('resources')
            if resources:
                for resource in resources:
                    q_results = model.Session.query(ResourceMultilang).filter(ResourceMultilang.resource_id == resource.get('id'), ResourceMultilang.lang == lang).all()
            
                    if q_results:
                        for result in q_results:
                            resource[result.field] = result.text

            #  MULTILANG - Localizing organization sub dict for the dataset read page
            organization = c.pkg_dict.get('organization')
            if organization:
                q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == organization.get('id'), GroupMultilang.lang == lang).all() 
                
                if q_results:
                    for result in q_results:
                        organization[result.field] = result.text

                c.pkg_dict['organization'] = organization

        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)

        package_type = c.pkg_dict['type'] or 'dataset'
        self._setup_template_variables(context, {'id': id},
                                       package_type=package_type)

        return render('package/resources.html',
                      extra_vars={'dataset_type': package_type})

    def new_resource(self, id, data=None, errors=None, error_summary=None):
        ''' FIXME: This is a temporary action to allow styling of the
        forms. '''
        if request.method == 'POST' and not data:
            save_action = request.params.get('save')
            data = data or clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(
                request.POST))))
            # we don't want to include save as it is part of the form
            del data['save']
            resource_id = data['id']
            del data['id']

            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author, 'auth_user_obj': c.userobj}

            # see if we have any data that we are trying to save
            data_provided = False
            for key, value in data.iteritems():
                if ((value or isinstance(value, cgi.FieldStorage))
                    and key != 'resource_type'):
                    data_provided = True
                    break

            if not data_provided and save_action != "go-dataset-complete":
                if save_action == 'go-dataset':
                    # go to final stage of adddataset
                    redirect(h.url_for(controller='package',
                                       action='edit', id=id))
                # see if we have added any resources
                try:
                    data_dict = get_action('package_show')(context, {'id': id})
                except NotAuthorized:
                    abort(401, _('Unauthorized to update dataset'))
                except NotFound:
                    abort(404,
                      _('The dataset {id} could not be found.').format(id=id))
                if not len(data_dict['resources']):
                    # no data so keep on page
                    msg = _('You must add at least one data resource')
                    # On new templates do not use flash message
                    if g.legacy_templates:
                        h.flash_error(msg)
                        redirect(h.url_for(controller='package',
                                           action='new_resource', id=id))
                    else:
                        errors = {}
                        error_summary = {_('Error'): msg}
                        return self.new_resource(id, data, errors, error_summary)
                # XXX race condition if another user edits/deletes
                data_dict = get_action('package_show')(context, {'id': id})
                get_action('package_update')(
                    dict(context, allow_state_change=True),
                    dict(data_dict, state='active'))
                redirect(h.url_for(controller='package',
                                   action='read', id=id))

            lang = get_lang()[0]
            data['package_id'] = id
            try:
                if resource_id:
                    data['id'] = resource_id
                    get_action('resource_update')(context, data)

                    #  MULTILANG - Updating existing record in multilang table
                    q_results = model.Session.query(ResourceMultilang).filter(ResourceMultilang.resource_id == resource_id, ResourceMultilang.lang == lang).all()
                    if q_results:
                        for result in q_results:
                            result.text = data.get(result.field)
                            result.save()
                else:
                    get_action('resource_create')(context, data)

                    #  MULTILANG - Creating new resource for multilang table
                    # A Package can have more resource with the same name, so we get the latest created in this case
                    r = model.Session.query(model.Resource).filter(model.Resource.name == data.get('name')).order_by(model.Resource.created.desc()).first()
                    if r:
                        log.info('Localised fields are missing in resource_multilang table, persisting ...')
                        session = model.Session
                        try:
                            session.add_all([
                                ResourceMultilang(resource_id=r.id, field='name', lang=lang, text=data.get('name')),
                                ResourceMultilang(resource_id=r.id, field='description', lang=lang, text=data.get('description')),
                            ])

                            session.commit()
                        except Exception, e:
                            # on rollback, the same closure of state
                            # as that of commit proceeds. 
                            session.rollback()

                            log.error('Exception occurred while persisting DB objects: %s', e)
                            raise
            except ValidationError, e:
                errors = e.error_dict
                error_summary = e.error_summary
                return self.new_resource(id, data, errors, error_summary)
            except NotAuthorized:
                abort(401, _('Unauthorized to create a resource'))
            except NotFound:
                abort(404,
                    _('The dataset {id} could not be found.').format(id=id))
            if save_action == 'go-metadata':
                # XXX race condition if another user edits/deletes
                data_dict = get_action('package_show')(context, {'id': id})
                get_action('package_update')(
                    dict(context, allow_state_change=True),
                    dict(data_dict, state='active'))
                redirect(h.url_for(controller='package',
                                   action='read', id=id))
            elif save_action == 'go-dataset':
                # go to first stage of add dataset
                redirect(h.url_for(controller='package',
                                   action='edit', id=id))
            elif save_action == 'go-dataset-complete':
                # go to first stage of add dataset
                redirect(h.url_for(controller='package',
                                   action='read', id=id))
            else:
                # add more resources
                redirect(h.url_for(controller='package',
                                   action='new_resource', id=id))

        # get resources for sidebar
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj}
        try:
            pkg_dict = get_action('package_show')(context, {'id': id})
        except NotFound:
            abort(404, _('The dataset {id} could not be found.').format(id=id))
        try:
            check_access(
                'resource_create', context, {"package_id": pkg_dict["id"]})
        except NotAuthorized:
            abort(401, _('Unauthorized to create a resource for this package'))

        package_type = pkg_dict['type'] or 'dataset'

        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary, 'action': 'new',
                'resource_form_snippet': self._resource_form(package_type),
                'dataset_type': package_type}
        vars['pkg_name'] = id
        # required for nav menu
        vars['pkg_dict'] = pkg_dict
        template = 'package/new_resource_not_draft.html'
        if pkg_dict['state'].startswith('draft'):
            vars['stage'] = ['complete', 'active']
            template = 'package/new_resource.html'
        return render(template, extra_vars=vars)