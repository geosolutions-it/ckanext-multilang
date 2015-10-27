import logging
from urllib import urlencode

from pylons.i18n import get_lang

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.maintain as maintain
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.authz as authz
import ckan.lib.plugins
import ckan.plugins as plugins
import ckan.lib.navl.dictization_functions as dict_fns

from ckan.common import OrderedDict, c, g, request, _

from ckanext.multilang.model import PackageMultilang, GroupMultilang, TagMultilang
from ckan.controllers.group import GroupController

log = logging.getLogger(__name__)

render = base.render
abort = base.abort

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

lookup_group_plugin = ckan.lib.plugins.lookup_group_plugin
lookup_group_controller = ckan.lib.plugins.lookup_group_controller

class MultilangGroupController(GroupController):

    def index(self):
        group_type = self._guess_group_type()

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'with_private': False}

        q = c.q = request.params.get('q', '')
        data_dict = {'all_fields': True, 'q': q, 'type': group_type or 'group'}
        sort_by = c.sort_by_selected = request.params.get('sort')
        if sort_by:
            data_dict['sort'] = sort_by
        try:
            self._check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        # pass user info to context as needed to view private datasets of
        # orgs correctly
        if c.userobj:
            context['user_id'] = c.userobj.id
            context['user_is_admin'] = c.userobj.sysadmin

        results = self._action('group_list')(context, data_dict)

        c.page = h.Page(
            collection=results,
            page = self._get_page_number(request.params),
            url=h.pager_url,
            items_per_page=21
        )

        log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')
        for item in c.page.items:   
            lang = get_lang()[0]
            
            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == item.get('id'), GroupMultilang.lang == lang).all() 

            if q_results:
                for result in q_results:
                    item[result.field] = result.text
                    if result.field == 'title':
                        item['display_name'] = result.text


        return render(self._index_template(group_type),
                      extra_vars={'group_type': group_type})
    
    def _read(self, id, limit, group_type):
        ''' This is common code used by both read and bulk_process'''
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True, 'extras_as_string': True}

        q = c.q = request.params.get('q', '')
        # Search within group
        if c.group_dict.get('is_organization'):
            q += ' owner_org:"%s"' % c.group_dict.get('id')
        else:
            q += ' groups:"%s"' % c.group_dict.get('name')

        c.description_formatted = h.render_markdown(c.group_dict.get('description'))

        context['return_query'] = True

        # c.group_admins is used by CKAN's legacy (Genshi) templates only,
        # if we drop support for those then we can delete this line.
        c.group_admins = authz.get_group_or_org_admin_ids(c.group.id)

        page = self._get_page_number(request.params)

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']
        sort_by = request.params.get('sort', None)

        def search_url(params):
            controller = lookup_group_controller(group_type)
            action = 'bulk_process' if c.action == 'bulk_process' else 'read'
            url = h.url_for(controller=controller, action=action, id=id)
            params = [(k, v.encode('utf-8') if isinstance(v, basestring)
                       else str(v)) for k, v in params]
            return url + u'?' + urlencode(params)

        def drill_down_url(**by):
            return h.add_url_param(alternative_url=None,
                                   controller='group', action='read',
                                   extras=dict(id=c.group_dict.get('name')),
                                   new_params=by)

        c.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller='group', action='read',
                                      extras=dict(id=c.group_dict.get('name')))

        c.remove_field = remove_field

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            c.fields = []
            search_extras = {}
            for (param, value) in request.params.items():
                if not param in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        q += ' %s: "%s"' % (param, value)
                    else:
                        search_extras[param] = value

            fq = 'capacity:"public"'
            user_member_of_orgs = [org['id'] for org
                                   in h.organizations_available('read')]

            if (c.group and c.group.id in user_member_of_orgs):
                fq = ''
                context['ignore_capacity_check'] = True

            facets = OrderedDict()

            default_facet_titles = {'organization': _('Organizations'),
                                    'groups': _('Groups'),
                                    'tags': _('Tags'),
                                    'res_format': _('Formats'),
                                    'license_id': _('Licenses')}

            for facet in g.facets:
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            self._update_facet_titles(facets, group_type)

            if 'capacity' in facets and (group_type != 'organization' or
                                         not user_member_of_orgs):
                del facets['capacity']

            c.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': fq,
                'facet.field': facets.keys(),
                'rows': limit,
                'sort': sort_by,
                'start': (page - 1) * limit,
                'extras': search_extras
            }

            context_ = dict((k, v) for (k, v) in context.items() if k != 'schema')
            query = get_action('package_search')(context_, data_dict)

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )

            c.group_dict['package_count'] = query['count']

            lang = get_lang()[0]
            
            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == c.group_dict.get('id'), GroupMultilang.lang == lang).all() 

            if q_results:
                for result in q_results:
                    c.group_dict[result.field] = result.text
                    if result.field == 'title':
                        c.group_dict['display_name'] = result.text
            
            c.facets = query['facets']
            maintain.deprecate_context_item('facets',
                                            'Use `c.search_facets` instead.')

            c.search_facets = query['search_facets']
            c.search_facets_limits = {}
            for facet in c.facets.keys():
                limit = int(request.params.get('_%s_limit' % facet,
                                               g.facets_default_number))
                c.search_facets_limits[facet] = limit

            # MULTILANG - Localizing Organizations display names in Facet list
            organizations = c.search_facets.get('organization')

            for org in organizations.get('items'):
                q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.name == org.get('name'), GroupMultilang.lang == lang).all() 

                if q_results:
                    for result in q_results:
                        if result.field == 'title':
                            org['display_name'] = result.text

            # MULTILANG - Localizing Groups display names in Facet list
            groups = c.search_facets.get('groups')
            for group in groups.get('items'):
                q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.name == group.get('name'), GroupMultilang.lang == lang).all() 

                if q_results:
                    for result in q_results:
                        if result.field == 'title':
                            group['display_name'] = result.text

             # MULTILANG - Localizing Tags display names in Facet list
            tags = c.search_facets.get('tags')
            for tag in tags.get('items'):
                localized_tag = TagMultilang.by_name(tag.get('name'), lang)

                if localized_tag:
                    tag['display_name'] = localized_tag.text

            c.page.items = query['results']
            
            # MULTILANG - Localizing Datasets names and descriptions in search list
            log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')

            for item in c.page.items:
                lang = get_lang()[0]

                q_results = model.Session.query(PackageMultilang).filter(PackageMultilang.package_id == item.get('id'), PackageMultilang.lang == lang).all() 

                if q_results:
                    for result in q_results:
                        item[result.field] = result.text
                
            c.sort_by_selected = sort_by

        except search.SearchError, se:
            log.error('Group search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])

        self._setup_template_variables(context, {'id':id},
            group_type=group_type)

    def _save_new(self, context, group_type=None):
        try:
            data_dict = clean_dict(dict_fns.unflatten(
                tuplize_dict(parse_params(request.params))))
            data_dict['type'] = group_type or 'group'
            context['message'] = data_dict.get('log_message', '')
            data_dict['users'] = [{'name': c.user, 'capacity': 'admin'}]
            group = self._action('group_create')(context, data_dict)

            log.info('::::: Persisting localised metadata locale :::::')
            lang = get_lang()[0]

            session = model.Session
            try:
                session.add_all([
                    GroupMultilang(group_id=group.get('id'), name=group.get('name'), field='title', lang=lang, text=group.get('title')),
                    GroupMultilang(group_id=group.get('id'), name=group.get('name'), field='description', lang=lang, text=group.get('description')),
                ])

                session.commit()
            except Exception, e:
                # on rollback, the same closure of state
                # as that of commit proceeds. 
                session.rollback()

                log.error('Exception occurred while persisting DB objects: %s', e)
                raise

            # Redirect to the appropriate _read route for the type of group
            h.redirect_to(group['type'] + '_read', id=group['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % '')
        except NotFound, e:
            abort(404, _('Group not found'))
        except dict_fns.DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def edit(self, id, data=None, errors=None, error_summary=None):
        group_type = self._ensure_controller_matches_group_type(
            id.split('@')[0])

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'save': 'save' in request.params,
                   'for_edit': True,
                   'parent': request.params.get('parent', None)
                   }
        data_dict = {'id': id, 'include_datasets': False}

        if context['save'] and not data:
            return self._save_edit(id, context)

        try:
            data_dict['include_datasets'] = False
            old_data = self._action('group_show')(context, data_dict)
            c.grouptitle = old_data.get('title')
            c.groupname = old_data.get('name')
            data = data or old_data
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % '')

        group = context.get("group")
        c.group = group
        c.group_dict = self._action('group_show')(context, data_dict)

        log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')

        lang = get_lang()[0]

        q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == data.get('id'), GroupMultilang.lang == lang).all()

        if q_results:
            for result in q_results:
                data[result.field] = result.text
                c.group_dict[result.field] = result.text
                if result.field == 'title':
                    c.group_dict['display_name'] = result.text

        try:
            self._check_access('group_update', context)
        except NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary, 'action': 'edit',
                'group_type': group_type}

        self._setup_template_variables(context, data, group_type=group_type)
        c.form = render(self._group_form(group_type), extra_vars=vars)
        return render(self._edit_template(c.group.type),
                      extra_vars={'group_type': group_type})

    def _save_edit(self, id, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            context['allow_partial_update'] = True
            group = self._action('group_update')(context, data_dict)
            if id != group['name']:
                self._force_reindex(group)

            log.info(':::::::::::: Saving the corresponding localized title and abstract :::::::::::::::')

            lang = get_lang()[0]

            q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == group.get('id')).all()

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

            if create_new == True:
                log.info(':::::::::::: Localized fields are missing in package_multilang table, persisting defaults using values in the table group :::::::::::::::')
                session = model.Session
                try:
                    session.add_all([
                        GroupMultilang(group_id=group.get('id'), name=group.get('name'), field='title', lang=lang, text=group.get('title')),
                        GroupMultilang(group_id=group.get('id'), name=group.get('name'), field='description', lang=lang, text=group.get('description')),
                    ])

                    session.commit()
                except Exception, e:
                    # on rollback, the same closure of state
                    # as that of commit proceeds. 
                    session.rollback()

                    log.error('Exception occurred while persisting DB objects: %s', e)
                    raise

            h.redirect_to('%s_read' % group['type'], id=group['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)
        except NotFound, e:
            abort(404, _('Group not found'))
        except dict_fns.DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)
    
    def about(self, id):
        group_type = self._ensure_controller_matches_group_type(id)
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        c.group_dict = self._get_group_dict(id)

        log.info(':::::::::::: Retrieving the corresponding localized title and abstract :::::::::::::::')

        # Localizing Organizations in about page
        lang = get_lang()[0]

        q_results = model.Session.query(GroupMultilang).filter(GroupMultilang.group_id == c.group_dict.get('id'), GroupMultilang.lang == lang).all() 

        if q_results:
            for result in q_results:
                c.group_dict[result.field] = result.text
                if result.field == 'title':
                    c.group_dict['display_name'] = result.text

        group_type = c.group_dict['type']
        self._setup_template_variables(context, {'id': id},
                                       group_type=group_type)
        return render(self._about_template(group_type),
                      extra_vars={'group_type': group_type})