"""
Tests for the fix that prevents resource updates from corrupting package-level
translations in the multilang extension.

When a resource is created/updated/deleted, CKAN internally calls package_update,
which triggers after_dataset_update. Without the fix, the package multilang entries
for the current session language would be overwritten with stale core-table data.

The fix uses a context flag set by before_resource_create/update/delete to signal
to after_dataset_update that it should skip the package multilang update.
"""
import unittest
from unittest.mock import patch


class TestResourceUpdateFix(unittest.TestCase):
    """Tests that resource operations do not corrupt package multilang entries."""

    def _make_plugin(self):
        from ckanext.multilang.plugin import MultilangPlugin
        return MultilangPlugin()

    def test_before_resource_create_sets_flag(self):
        """before_resource_create should set the skip flag in context."""
        plugin = self._make_plugin()
        context = {}
        plugin.before_resource_create(context, {})
        self.assertTrue(context.get(plugin._RESOURCE_OP_FLAG))

    def test_before_resource_update_sets_flag(self):
        """before_resource_update should set the skip flag in context."""
        plugin = self._make_plugin()
        context = {}
        plugin.before_resource_update(context, {}, {})
        self.assertTrue(context.get(plugin._RESOURCE_OP_FLAG))

    def test_before_resource_delete_sets_flag(self):
        """before_resource_delete should set the skip flag in context."""
        plugin = self._make_plugin()
        context = {}
        plugin.before_resource_delete(context, {}, [])
        self.assertTrue(context.get(plugin._RESOURCE_OP_FLAG))

    def test_after_resource_create_clears_flag(self):
        """after_resource_create should remove the skip flag from context."""
        plugin = self._make_plugin()
        context = {plugin._RESOURCE_OP_FLAG: True}
        with patch('ckanext.multilang.plugin.helpers.getLanguage', return_value=None):
            plugin.after_resource_create(context, {})
        self.assertNotIn(plugin._RESOURCE_OP_FLAG, context)

    def test_after_resource_update_clears_flag(self):
        """after_resource_update should remove the skip flag from context."""
        plugin = self._make_plugin()
        context = {plugin._RESOURCE_OP_FLAG: True}
        with patch('ckanext.multilang.plugin.helpers.getLanguage', return_value=None):
            plugin.after_resource_update(context, {})
        self.assertNotIn(plugin._RESOURCE_OP_FLAG, context)

    def test_after_resource_delete_clears_flag(self):
        """after_resource_delete should remove the skip flag from context."""
        plugin = self._make_plugin()
        context = {plugin._RESOURCE_OP_FLAG: True}
        plugin.after_resource_delete(context, [])
        self.assertNotIn(plugin._RESOURCE_OP_FLAG, context)

    def test_after_dataset_update_skips_when_flag_set(self):
        """after_dataset_update must not update package multilang when the resource
        operation flag is present, preventing stale-data corruption."""
        plugin = self._make_plugin()
        context = {plugin._RESOURCE_OP_FLAG: True}
        with patch('ckanext.multilang.plugin.helpers.getLanguage', return_value='de'), \
             patch('ckanext.multilang.plugin.after_update_dataset') as mock_update:
            plugin.after_dataset_update(context, {'id': 'pkg-1', 'title': 'Italian Title'})
            mock_update.assert_not_called()

    def test_after_dataset_update_runs_normally_without_flag(self):
        """after_dataset_update must proceed normally when no resource operation flag
        is present (i.e. a direct package update from the user)."""
        plugin = self._make_plugin()
        context = {}
        pkg_dict = {'id': 'pkg-1', 'title': 'Deutscher Titel'}
        with patch('ckanext.multilang.plugin.helpers.getLanguage', return_value='de'), \
             patch('ckanext.multilang.plugin.after_update_dataset') as mock_update:
            plugin.after_dataset_update(context, pkg_dict)
            mock_update.assert_called_once_with(context, pkg_dict, 'de')

    def test_resource_update_hooks_manage_flag_on_reused_context(self):
        """Unit-test the plugin hook contract when the same context dict is reused.

        This does not exercise CKAN's real ``resource_update`` action stack; it
        only verifies that the plugin sets the skip flag before the dataset hook,
        that ``after_dataset_update`` respects that flag, and that the resource
        post-hook clears it afterwards.
        """
        plugin = self._make_plugin()
        context = {}

        with patch('ckanext.multilang.plugin.helpers.getLanguage', return_value='de'), \
             patch('ckanext.multilang.plugin.after_update_dataset') as mock_update, \
             patch('ckanext.multilang.plugin.after_update_resource'):

            plugin.before_resource_update(context, {}, {})
            self.assertTrue(context.get(plugin._RESOURCE_OP_FLAG))

            plugin.after_dataset_update(
                context, {'id': 'pkg-1', 'title': 'Italian Title'}
            )
            mock_update.assert_not_called()

            plugin.after_resource_update(context, {'id': 'res-1'})

        self.assertNotIn(plugin._RESOURCE_OP_FLAG, context)

    def test_flag_lifecycle_during_resource_create(self):
        """Simulate the full CKAN resource_create hook sequence."""
        plugin = self._make_plugin()
        context = {}
        pkg_update_calls = []

        with patch('ckanext.multilang.plugin.helpers.getLanguage', return_value='de'), \
             patch('ckanext.multilang.plugin.after_update_dataset',
                   side_effect=lambda *a: pkg_update_calls.append(a)), \
             patch('ckanext.multilang.plugin.after_create_resource'):

            plugin.before_resource_create(context, {})
            plugin.after_dataset_update(context, {'id': 'pkg-1'})
            plugin.after_resource_create(context, {'id': 'res-1'})

        self.assertEqual(pkg_update_calls, [],
                         "after_dataset_update should not be called during resource create")
        self.assertNotIn(plugin._RESOURCE_OP_FLAG, context)

    def test_flag_lifecycle_during_resource_delete(self):
        """Simulate the full CKAN resource_delete hook sequence."""
        plugin = self._make_plugin()
        context = {}
        pkg_update_calls = []

        with patch('ckanext.multilang.plugin.helpers.getLanguage', return_value='de'), \
             patch('ckanext.multilang.plugin.after_update_dataset',
                   side_effect=lambda *a: pkg_update_calls.append(a)):

            plugin.before_resource_delete(context, {}, [])
            plugin.after_dataset_update(context, {'id': 'pkg-1'})
            plugin.after_resource_delete(context, [])

        self.assertEqual(pkg_update_calls, [],
                         "after_dataset_update should not be called during resource delete")
        self.assertNotIn(plugin._RESOURCE_OP_FLAG, context)
