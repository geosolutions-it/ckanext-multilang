def delete_multilang_tag(entity):
    tags = TagMultilang.get_all(entity.name)
    for tag in tags:
        tag.delete()
        log.debug(f'--> delete TagMultilang: {tag.id}: lang -> {resource.lang}, name -> {tag.name}, text -> {tag.text}')
