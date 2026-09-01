import os
from unittest.mock import patch
from django.test import SimpleTestCase
from starpets_project.env_parsers import get_env_bool, get_env_list

class EnvParserTests(SimpleTestCase):
    
    @patch.dict(os.environ, {'TEST_BOOL': 'True'})
    def test_get_env_bool_true(self):
        self.assertEqual(get_env_bool('TEST_BOOL'), True)
        
    @patch.dict(os.environ, {'TEST_BOOL': 'true'})
    def test_get_env_bool_lowercase_true(self):
        self.assertEqual(get_env_bool('TEST_BOOL'), True)

    @patch.dict(os.environ, {'TEST_BOOL': 'False'})
    def test_get_env_bool_false(self):
        self.assertEqual(get_env_bool('TEST_BOOL'), False)

    @patch.dict(os.environ, {}, clear=True)
    def test_get_env_bool_missing_uses_default(self):
        self.assertEqual(get_env_bool('TEST_BOOL', False), False)

    @patch.dict(os.environ, {'TEST_LIST': '127.0.0.1, localhost'})
    def test_get_env_list_valid_string(self):
        self.assertEqual(get_env_list('TEST_LIST'), ['127.0.0.1', 'localhost'])
        
    @patch.dict(os.environ, {'TEST_LIST': ''})
    def test_get_env_list_empty_string(self):
        self.assertEqual(get_env_list('TEST_LIST', []), [])
