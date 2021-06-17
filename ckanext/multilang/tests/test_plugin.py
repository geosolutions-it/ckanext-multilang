import unittest
from ckanext.multilang.plugin import MultilangPlugin


class TestPlugin(unittest.TestCase):
    def test_plugin(self):
        self.assertTrue(MultilangPlugin())
