#!/bin/bash
ps -W | grep python | awk '{print $1}' | xargs kill -f
#./odoo.py --addons-path=addons,../design-themes -r odoo -w odoo -d themes --db-filter=blog
#./cygdrive/c/Python27/python.exe ./odoo.py --addons-path=addons,../design-themes -r odoo -w odoo -d themes --db-filter=blog
