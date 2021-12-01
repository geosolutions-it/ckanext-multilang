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
        log.info('Localised fields are missing in resource_multilang table, persisting ...')
        ResourceMultilang.persist(resource, lang)


def after_update_resource(context, resource, lang):
    r = model.Resource.get(resource.get('id'))
    if r:
        r = model_dictize.resource_dictize(r, {'model': model, 'session': model.Session})

        q_results = ResourceMultilang.get_for_resource_id_and_lang(r.get('id'), lang)
        if q_results and q_results.count() > 0:
            for result in q_results:
                result.text = r.get(result.field)
                result.save()
        else:
            log.info('Localised fields are missing in resource_multilang table, persisting ...')
            ResourceMultilang.persist(r, lang)

# def before_view_resource(data):


def delete_multilang_resource(entity):
    resources = ResourceMultilang.get_for_resource_id(entity.id)
    for resource in resources:
        resource.delete()
        log.debug(f'--> delete ResourceMultilang: {resource.field}: lang -> {resource.lang}, text -> {resource.text}')