# -*- coding: utf-8 -*-
import unittest2
from openerp import fields

class TestFieldToColumn(unittest2.TestCase):
    def test_char(self):
        field = fields.Char(string="test string", required=True)
        column = field.to_column()

        self.assertEqual(column.string, "test string")
        self.assertTrue(column.required)
