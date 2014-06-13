# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2014 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import contextlib
import functools
import imp
import importlib
import itertools
import logging
import os
import re
import sys
import time
import types
import unittest
from os.path import join as opj
import pkg_resources

import unittest2

import odoo
import odoo.tools as tools
import odoo.release as release
from odoo.tools.safe_eval import safe_eval as eval

MANIFEST = '__openerp__.py'

_logger = logging.getLogger(__name__)

# addons path as a list
ad_paths = []
hooked = False

# Modules already loaded
loaded = []

class AddonsHook(object):
    """ Makes modules accessible (solely) through odoo.addons.* (and
    openerp.addons.* for BC)
    """
    def find_module(self, name, path):
        if name.startswith(('odoo.addons.', 'openerp.addons.'))\
                and name.count('.') == 2:
            return self

    def load_module(self, name):
        assert name not in sys.modules

        # get canonical name
        new_name = re.sub(r'^openerp.addons.(\w+)$', r'odoo.addons.\g<1>', name)
        old_name = re.sub(r'^odoo.addons.(\w+)', r'openerp.addons.\g<1>', new_name)

        assert new_name not in sys.modules
        assert old_name not in sys.modules

        # get module name in addons paths
        _1, _2, addon_name = name.split('.')
        # load module
        f, path, (_suffix, _mode, type_) = imp.find_module(addon_name, ad_paths)
        if f: f.close()

        # TODO: fetch existing module from sys.modules if reloads permitted
        # create empty odoo.addons.* module, set name
        new_mod = types.ModuleType(new_name)
        new_mod.__loader__ = self

        # module toplevels can only be packages
        assert type_ == imp.PKG_DIRECTORY, "Odoo addon toplevel can only be a package"
        modfile = opj(path, '__init__.py')
        new_mod.__file__ = modfile
        new_mod.__path__ = [path]
        new_mod.__package__ = new_name

        # both base and alias should be in sys.modules to handle recursive and
        # corecursive situations
        sys.modules[old_name] = sys.modules[new_name] = new_mod

        # execute source in context of module *after* putting everything in
        # sys.modules
        execfile(modfile, new_mod.__dict__)

        # people import odoo.addons and expect odoo.addons.<module> to work
        setattr(odoo.addons, addon_name, new_mod)

        return sys.modules[name]
# need to register loader with setuptools as Jinja relies on it when using
# PackageLoader
pkg_resources.register_loader_type(AddonsHook, pkg_resources.DefaultProvider)

class OdooHook(object):
    """ Makes odoo package also available as openerp
    """

    def find_module(self, name, path):
        # openerp.addons.<identifier> should already be matched by AddonsHook,
        # only framework and subdirectories of modules should match
        if re.match(r'openerp\b', name):
            return self

    def load_module(self, name):
        assert name not in sys.modules

        canonical = re.sub(r'^openerp(.*)', r'odoo\g<1>', name)

        if canonical in sys.modules:
            mod = sys.modules[canonical]
        else:
            # probable failure: canonical execution calling old naming -> corecursion
            mod = importlib.import_module(canonical)

        # just set the original module at the new location. Don't proxy,
        # it breaks *-import (unless you can find how `from a import *` lists
        # what's supposed to be imported by `*`, and manage to override it)
        sys.modules[name] = mod

        return sys.modules[name]

def initialize_sys_path():
    """
    Setup an import-hook to be able to import OpenERP addons from the different
    addons paths.

    This ensures something like ``import crm`` (or even
    ``import openerp.addons.crm``) works even if the addons are not in the
    PYTHONPATH.
    """
    global ad_paths
    global hooked

    dd = tools.config.addons_data_dir
    if dd not in ad_paths:
        ad_paths.append(dd)

    for ad in tools.config['addons_path'].split(','):
        ad = os.path.abspath(tools.ustr(ad.strip()))
        if ad not in ad_paths:
            ad_paths.append(ad)

    # add base module path
    base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'addons'))
    if base_path not in ad_paths:
        ad_paths.append(base_path)

    if not hooked:
        sys.meta_path.append(AddonsHook())
        sys.meta_path.append(OdooHook())
        hooked = True

def get_module_path(module, downloaded=False, display_warning=True):
    """Return the path of the given module.

    Search the addons paths and return the first path where the given
    module is found. If downloaded is True, return the default addons
    path if nothing else is found.

    """
    initialize_sys_path()
    for adp in ad_paths:
        if os.path.exists(opj(adp, module)) or os.path.exists(opj(adp, '%s.zip' % module)):
            return opj(adp, module)

    if downloaded:
        return opj(tools.config.addons_data_dir, module)
    if display_warning:
        _logger.warning('module %s: module not found', module)
    return False

def get_module_filetree(module, dir='.'):
    path = get_module_path(module)
    if not path:
        return False

    dir = os.path.normpath(dir)
    if dir == '.':
        dir = ''
    if dir.startswith('..') or (dir and dir[0] == '/'):
        raise Exception('Cannot access file outside the module')

    files = odoo.tools.osutil.listdir(path, True)

    tree = {}
    for f in files:
        if not f.startswith(dir):
            continue

        if dir:
            f = f[len(dir)+int(not dir.endswith('/')):]
        lst = f.split(os.sep)
        current = tree
        while len(lst) != 1:
            current = current.setdefault(lst.pop(0), {})
        current[lst.pop(0)] = None

    return tree

def get_module_resource(module, *args):
    """Return the full path of a resource of the given module.

    :param module: module name
    :param list(str) args: resource path components within module

    :rtype: str
    :return: absolute path to the resource

    TODO name it get_resource_path
    TODO make it available inside on osv object (self.get_resource_path)
    """
    mod_path = get_module_path(module)
    if not mod_path: return False
    resource_path = opj(mod_path, *args)
    if os.path.isdir(mod_path):
        # the module is a directory - ignore zip behavior
        if os.path.exists(resource_path):
            return resource_path
    return False

def get_module_icon(module):
    iconpath = ['static', 'description', 'icon.png']
    if get_module_resource(module, *iconpath):
        return ('/' + module + '/') + '/'.join(iconpath)
    return '/base/'  + '/'.join(iconpath)

def get_module_root(path):
    """
    Get closest module's root begining from path

        # Given:
        # /foo/bar/module_dir/static/src/...

        get_module_root('/foo/bar/module_dir/static/')
        # returns '/foo/bar/module_dir'

        get_module_root('/foo/bar/module_dir/')
        # returns '/foo/bar/module_dir'

        get_module_root('/foo/bar')
        # returns None

    @param path: Path from which the lookup should start

    @return:  Module root path or None if not found
    """
    while not os.path.exists(os.path.join(path, MANIFEST)):
        new_path = os.path.abspath(os.path.join(path, os.pardir))
        if path == new_path:
            return None
        path = new_path
    return path

def load_information_from_description_file(module, mod_path=None):
    """
    :param module: The name of the module (sale, purchase, ...)
    :param mod_path: Physical path of module, if not providedThe name of the module (sale, purchase, ...)
    """

    if not mod_path:
        mod_path = get_module_path(module)
    terp_file = mod_path and opj(mod_path, MANIFEST) or False
    if terp_file:
        info = {}
        if os.path.isfile(terp_file):
            # default values for descriptor
            info = {
                'application': False,
                'author': '',
                'auto_install': False,
                'category': 'Uncategorized',
                'depends': [],
                'description': '',
                'icon': get_module_icon(module),
                'installable': True,
                'license': 'AGPL-3',
                'name': False,
                'post_load': None,
                'version': '1.0',
                'web': False,
                'website': '',
                'sequence': 100,
                'summary': '',
            }
            info.update(itertools.izip(
                'depends data demo test init_xml update_xml demo_xml'.split(),
                iter(list, None)))

            f = tools.file_open(terp_file)
            try:
                info.update(eval(f.read()))
            finally:
                f.close()

            if 'active' in info:
                # 'active' has been renamed 'auto_install'
                info['auto_install'] = info['active']

            info['version'] = adapt_version(info['version'])
            return info

    #TODO: refactor the logger in this file to follow the logging guidelines
    #      for 6.0
    _logger.debug('module %s: no %s file found.', module, MANIFEST)
    return {}

def init_module_models(cr, module_name, obj_list):
    """ Initialize a list of models.

    Call _auto_init and init on each model to create or update the
    database tables supporting the models.

    TODO better explanation of _auto_init and init.

    """
    _logger.info('module %s: creating or updating database tables', module_name)
    todo = []
    for obj in obj_list:
        result = obj._auto_init(cr, {'module': module_name})
        if result:
            todo += result
        if hasattr(obj, 'init'):
            obj.init(cr)
        cr.commit()
    for obj in obj_list:
        obj._auto_end(cr, {'module': module_name})
        cr.commit()
    todo.sort(key=lambda x: x[0])
    for t in todo:
        t[1](cr, *t[2])
    cr.commit()

def load_openerp_module(module_name):
    """ Load an OpenERP module, if not already loaded.

    This loads the module and register all of its models, thanks to either
    the MetaModel metaclass, or the explicit instantiation of the model.
    This is also used to load server-wide module (i.e. it is also used
    when there is no model to register).
    """
    global loaded
    if module_name in loaded:
        return

    initialize_sys_path()
    try:
        mod_path = get_module_path(module_name)
        importlib.import_module('odoo.addons.' + module_name)

        # Call the module's post-load hook. This can done before any model or
        # data has been initialized. This is ok as the post-load hook is for
        # server-wide (instead of registry-specific) functionalities.
        info = load_information_from_description_file(module_name)
        if info['post_load']:
            getattr(sys.modules['odoo.addons.' + module_name], info['post_load'])()

    except Exception, e:
        msg = "Couldn't load module %s" % (module_name)
        _logger.critical(msg)
        _logger.critical(e)
        raise
    else:
        loaded.append(module_name)

def get_modules():
    """Returns the list of module names
    """
    def listdir(dir):
        def clean(name):
            name = os.path.basename(name)
            if name[-4:] == '.zip':
                name = name[:-4]
            return name

        def is_really_module(name):
            manifest_name = opj(dir, name, MANIFEST)
            zipfile_name = opj(dir, name)
            return os.path.isfile(manifest_name)
        return map(clean, filter(is_really_module, os.listdir(dir)))

    plist = []
    initialize_sys_path()
    for ad in ad_paths:
        plist.extend(listdir(ad))
    return list(set(plist))

def get_modules_with_version():
    modules = get_modules()
    res = dict.fromkeys(modules, adapt_version('1.0'))
    for module in modules:
        try:
            info = load_information_from_description_file(module)
            res[module] = info['version']
        except Exception:
            continue
    return res

def adapt_version(version):
    serie = release.major_version
    if version == serie or not version.startswith(serie + '.'):
        version = '%s.%s' % (serie, version)
    return version

def get_test_modules(module):
    """ Return a list of module for the addons potentialy containing tests to
    feed unittest2.TestLoader.loadTestsFromModule() """
    # Try to import the module
    module = 'odoo.addons.' + module + '.tests'
    try:
        importlib.import_module(module)
    except Exception, e:
        # If module has no `tests` sub-module, no problem.
        if str(e) != 'No module named tests':
            _logger.exception('Can not `import %s`.', module)
        return []

    # include submodules too
    result = [mod_obj for name, mod_obj in sys.modules.iteritems()
              if mod_obj # mod_obj can be None
              if name.startswith(module)
              if re.search(r'test_\w+$', name)]
    return result

# Use a custom stream object to log the test executions.
class TestStream(object):
    def __init__(self, logger_name='openerp.tests'):
        self.logger = logging.getLogger(logger_name)
        self.r = re.compile(r'^-*$|^ *... *$|^ok$')
    def flush(self):
        pass
    def write(self, s):
        if self.r.match(s):
            return
        first = True
        level = logging.ERROR if s.startswith(('ERROR', 'FAIL', 'Traceback')) else logging.INFO
        for c in s.splitlines():
            if not first:
                c = '` ' + c
            first = False
            self.logger.log(level, c)

current_test = None

def runs_at(test, hook, default):
    # by default, tests do not run post install
    test_runs = getattr(test, hook, default)

    # for a test suite, we're done
    if not isinstance(test, unittest.TestCase):
        return test_runs

    # otherwise check the current test method to see it's been set to a
    # different state
    method = getattr(test, test._testMethodName)
    return getattr(method, hook, test_runs)

runs_at_install = functools.partial(runs_at, hook='at_install', default=True)
runs_post_install = functools.partial(runs_at, hook='post_install', default=False)

def run_unit_tests(module_name, dbname, position=runs_at_install):
    """
    :returns: ``True`` if all of ``module_name``'s tests succeeded, ``False``
              if any of them failed.
    :rtype: bool
    """
    global current_test
    current_test = module_name
    mods = get_test_modules(module_name)
    r = True
    for m in mods:
        tests = unwrap_suite(unittest2.TestLoader().loadTestsFromModule(m))
        suite = unittest2.TestSuite(itertools.ifilter(position, tests))

        if suite.countTestCases():
            t0 = time.time()
            t0_sql = odoo.sql_db.sql_counter
            _logger.info('%s running tests.', m.__name__)
            result = unittest2.TextTestRunner(verbosity=2, stream=TestStream(m.__name__)).run(suite)
            if time.time() - t0 > 5:
                _logger.log(25, "%s tested in %.2fs, %s queries", m.__name__, time.time() - t0, odoo.sql_db.sql_counter - t0_sql)
            if not result.wasSuccessful():
                r = False
                _logger.error("Module %s: %d failures, %d errors", module_name, len(result.failures), len(result.errors))

    current_test = None
    return r

def unwrap_suite(test):
    """
    Attempts to unpack testsuites (holding suites or cases) in order to
    generate a single stream of terminals (either test cases or customized
    test suites). These can then be checked for run/skip attributes
    individually.

    An alternative would be to use a variant of @unittest2.skipIf with a state
    flag of some sort e.g. @unittest2.skipIf(common.runstate != 'at_install'),
    but then things become weird with post_install as tests should *not* run
    by default there
    """
    if isinstance(test, unittest.TestCase):
        yield test
        return

    subtests = list(test)
    # custom test suite (no test cases)
    if not len(subtests):
        yield test
        return

    for item in itertools.chain.from_iterable(
            itertools.imap(unwrap_suite, subtests)):
        yield item

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
