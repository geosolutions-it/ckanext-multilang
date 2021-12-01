import logging

import ckan.lib.dictization.model_dictize as model_dictize
import ckan.model as model

from ckanext.multilang.model import (
    ResourceMultilang,
)

log = logging.getLogger(__name__)


def after_create_resource(context, resource, lang):
    r = model.Resource.get(resource.get('id'))
    if r:
        log.debug(f'Creating localized resource fields id:{r.id} lang:{lang}')
        ResourceMultilang.persist(resource, lang)


def after_update_resource(context, resource, lang):
    r = model.Resource.get(resource.get('id'))
    if r:
        r = model_dictize.resource_dictize(r, {'model': model, 'session': model.Session})

        q_results = ResourceMultilang.get_for_resource_id_and_lang(r.get('id'), lang)
        if q_results and q_results.count() > 0:
            for db_item in q_results:
                field_name = db_item.field
                log.debug(f'Updating localized RESOURCE field {field_name} lang:{lang} OLD:{db_item.text}')
                log.debug(f'Updating localized RESOURCE field {field_name} lang:{lang} NEW:{r.get(field_name)}')
                db_item.text = r.get(field_name)
                db_item.save()
        else:
            log.info('Localized fields are missing in resource_multilang table, persisting ...')
            ResourceMultilang.persist(r, lang)

# def before_view_resource(data):