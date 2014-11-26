#!/bin/sh

set -e

ODOO_CONFIGURATION_FILE=/etc/openerp/openerp-server.conf
ODOO_CONFIGURATION_DIR=/etc/openerp
ODOO_DATA_DIR=/var/lib/openerp
ODOO_GROUP="openerp"
ODOO_LOG_DIR=/var/log/openerp
ODOO_USER="openerp"

if ! getent passwd | grep -q "^openerp:"; then
    groupadd $ODOO_GROUP
    adduser --system --no-create-home $ODOO_USER -g $ODOO_GROUP
fi
# Register "openerp" as a postgres superuser 
su - postgres -c "createuser -s openerp" 2> /dev/null || true
# Configuration file
mkdir -p $ODOO_CONFIGURATION_DIR
echo "[options]
; This is the password that allows database operations:
; admin_passwd = admin
db_host = False
db_port = False
db_user = openerp
db_password = False
addons_path = /usr/lib/python2.6/site-packages/openerp/addons
" > $ODOO_CONFIGURATION_FILE
chown $ODOO_USER:$ODOO_GROUP $ODOO_CONFIGURATION_FILE
chmod 0640 $ODOO_CONFIGURATION_FILE
# Log
mkdir -p $ODOO_LOG_DIR
chown $ODOO_USER:$ODOO_GROUP $ODOO_LOG_DIR
chmod 0750 $ODOO_LOG_DIR
# Data dir
mkdir -p $ODOO_DATA_DIR
chown $ODOO_USER:$ODOO_GROUP $ODOO_DATA_DIR

INIT_FILE=/lib/systemd/system/odoo.service
touch $INIT_FILE
chmod 0700 $INIT_FILE
cat << 'EOF' > $INIT_FILE
[Unit]
Description=Odoo Open Source ERP and CRM
After=network.target

[Service]
Type=simple
User=odoo
Group=odoo
ExecStart=/usr/bin/odoo.py --config=/etc/odoo/openerp-server.conf

[Install]
WantedBy=multi-user.target
EOF
easy_install pyPdf vatnumber pydot
