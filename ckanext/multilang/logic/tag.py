import logging

import ckanext.multilang.helpers as helpers
from ckanext.multilang.model import TagMultilang

log = logging.getLogger(__name__)


def delete_multilang_tag(entity):
    tags = TagMultilang.get_for_tag_id(entity.tag_id)
    for tag in tags:
        tag.delete()
        log.debug(f'--> delete TagMultilang: {tag.id}: lang -> {tag.lang}, name -> {tag.name}, text -> {tag.text}')
