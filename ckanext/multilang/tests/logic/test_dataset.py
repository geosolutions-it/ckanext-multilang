import uuid

import pytest
from ckan import plugins
import ckan.tests.factories as factories
from ckan.model import Package, Resource, Group, Tag
import ckan.tests.helpers as helpers

from ckanext.multilang.model import PackageMultilang, ResourceMultilang, GroupMultilang, TagMultilang
import ckan.plugins.toolkit as tk

@pytest.mark.usefixtures('clean_postgis', 'clean_db', 'clean_index', 'create_postgis_tables',
                         'multilang_setup', 'with_request_context'
)
class TestDeleteDataset(object):
    def test_delete_dataset(self):
        user = factories.Sysadmin()
        context = {"user": user["name"], "ignore_auth": True}
        dataset = helpers.call_action(
            "package_create",
            context=context,
            id="123456789",
            identifier="123456789",
            name="test-dataset",
            theme='theme_1', frequency='ANNUAL', modified='01/01/2021',
            notes='notes'
        )

        # create multilang package
        multilang_package = PackageMultilang(
            package_id=dataset.get('id'),
            lang='en',
            field='holder_name',
            field_type='extra',
            text='test holder'
        )
        multilang_package.save()

        params = {
            "package_id": dataset.get('id'),
            "url": "http://data",
            "name": "A nice resource",
            "description": "A nice resource",
        }
        resource = helpers.call_action("resource_create", context, **params)

        # create multilang resource
        multilang_resource = ResourceMultilang(
            resource_id=resource.get('id'),
            lang='en',
            field='resource_name',
            text='resource holder'
        )
        multilang_resource.save()

        group = helpers.call_action("group_create", context=context, name="test-group")

        # create multilang group
        multilang_group = GroupMultilang(
            group_id=group.get('id'),
            name=group.get('name'),
            lang='en',
            field='group_name',
            text='group holder'
        )
        multilang_group.save()

        data = {'name': 'country_codes'}
        vocab = tk.get_action('vocabulary_create')(context, data)
        data = {'name': 'en', 'vocabulary_id': vocab['id']}
        tag = tk.get_action('tag_create')(context, data)

        # create multilang tag
        multilang_tag = TagMultilang(
            tag_id=tag.get('id'),
            tag_name=tag.get('name'),
            lang='en',
            text='tag holder'
        )
        multilang_tag.save()

        helpers.call_action(
            "tag_delete",
            context=context,
            id=tag.get('id')
        )

        helpers.call_action(
            "group_delete",
            context=context,
            id=group.get('id')
        )

        helpers.call_action(
            "resource_delete",
            context=context,
            id=resource.get('id')
        )

        helpers.call_action(
            "package_delete",
            context=context,
            id=dataset.get('id')
        )

        multi_lang_packages = PackageMultilang.get_for_package(dataset.get('id'))
        groups = GroupMultilang.get_for_group_id(group.get('id'))
        resources = ResourceMultilang.get_for_resource_id(resource.get('id'))
        tags = TagMultilang.get_for_tag_id(tag.get('id'))

        print(multi_lang_packages)
        print(groups)
        print(tags)
        print(resources)
        assert not multi_lang_packages
        assert not groups
        assert not tags

