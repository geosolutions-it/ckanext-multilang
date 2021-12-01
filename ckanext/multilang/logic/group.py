def delete_multilang_group(entity):
    groups = GroupMultilang.get_for_group_id(entity.id)
    for group in groups:
        group.delete()
        log.debug(f'--> delete GroupMultilang: {group.name}')