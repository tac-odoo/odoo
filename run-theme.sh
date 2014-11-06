#!/bin/bash
#./odoo.py -r odoo -w odoo -d odooblog --db-filter=odooblog
./odoo.py --addons-path=addons,../design-themes -r odoo -w odoo -d themes --db-filter=themes
