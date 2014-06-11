# -*- coding: utf-8 -*-
from openerp.tests import common

class test_inherits(common.TransactionCase):

    def test_access_from_child_to_parent_model(self):
        """ check whether added field in model is accessible from children models (_inherits) """
        # This test checks if the new added column of a parent model
        # is accessible from the child model. This test has been written
        # to verify the purpose of the inheritance computing of the class
        # in the openerp.osv.orm._build_model.
        mother = self.registry('test.inherit.mother')
        daugther = self.registry('test.inherit.daugther')

        self.assertIn('field_in_mother', mother._fields)
        self.assertIn('field_in_mother', daugther._fields)

    def test_field_extension(self):
        """ check the extension of a field in an inherited model """
        mother = self.registry('test.inherit.mother')
        field = mother._fields['name']

        # the field should inherit required=True, and have a default value
        self.assertTrue(field.required)
        self.assertEqual(field.default, 'Unknown')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
