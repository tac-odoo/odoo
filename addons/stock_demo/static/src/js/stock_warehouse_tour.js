(function () {
    'use strict';

    var _t = openerp._t;

    openerp.Tour.register({
        id:   'stock_warehouse',
        name: _t("Create Warehouse"),
        steps: [
            {
                title:     _t("Welcome to Warehouse Tutorial"),
                content:   _t("Let's go through the first steps to create Warehouse."),
                popover:   { next: _t("Start Tutorial"), end: _t("Skip") },
                onload:    function(Tour){
                    window.location.href = "/web/#action=stock.action_warehouse_form";
                }
            },
            {
                element:   '.oe_button.oe_list_add.oe_highlight',
                placement: 'bottom',
                title:     _t("Create"),
                content:   _t("Use this Create button to create a new Warehouse."),
                popover:   { fixed: true },
            },
            {
                element:   '.oe_form_field.oe_form_field_char.oe_form_required:first input',
                placement: 'bottom',
                title:     _t("Warehouse Name"),
                content:   _t("Give the Proper Warehouse Name"),
                popover:   { fixed: true },
            },
            {
                waitNot:   '.oe_form_field.oe_form_field_char.oe_form_required:first input:text[value=""]',
                element:   '.oe_form_field.oe_form_field_char.oe_form_required:eq(1) input',
                placement: 'bottom',
                title:     _t("ShortName"),
                content:   _t("Give the shortname Name"),
                popover:   { fixed: true },
            },
            {
                waitNot:   '.oe_form_field.oe_form_field_char.oe_form_required:eq(1) input:text[value=""]',
                element:   '.oe_button.oe_form_button_save.oe_highlight',
                placement: 'bottom',
                title:     _t("Save"),
                content:   _t("Click to save the record"),
                popover:   { fixed: true },
            },
            {
                waitFor:   '.oe_button.oe_form_button_edit:visible',
                title:     "Thanks!",
                content:   _t("Here you can see the Routes and other features for warehouse."),
                popover:   { next: _t("Close Tutorial") },
            },
        ]
    });

}());
