import logging

import ckanext.multilang.helpers as helpers
from ckanext.multilang.model import GroupMultilang

log = logging.getLogger(__name__)

def delete_multilang_group(entity):
    groups = GroupMultilang.get_for_group_id(entity.id)
    for group in groups:
        group.delete()
        log.debug(f'--> delete GroupMultilang: {group.name}')