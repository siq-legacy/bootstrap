#!/usr/bin/env python
# TODO Break out into multiple modules
# TODO Support windows?
import subprocess
import urllib2
import sys
import os
from ConfigParser import ConfigParser

# Common strings
BOOTSTRAP = 'bootstrap'
SCRIPT_NAME = sys.argv[0]
SCRIPT_VERSION = '0.1'
DESCRIPTION = 'provides a low-level, simple interface to CloudIQ which allows it to provision, update and test the server'
STATIC_CONFIG = '/etc/%s' % BOOTSTRAP
DYNAMIC_CONFIG = '/var/%s' % BOOTSTRAP
DEFAULT_CONFIG_FILE = '%s/bootstrap.ini' % STATIC_CONFIG
VERSION = 'version'
PRODUCT = 'product'
PRODUCTS = 'products'
REPOSITORY = 'repository'
SERVER = 'server'
KEY = 'key'
VALUE = 'value'
REVISION = 'revision'
CALLBACK = 'callback'
MODE = 'mode'
SPAWN = 'spawn'
TYPE = 'type'
SERVER_TYPE = '%s-%s' % (SERVER, TYPE)
BOOTSTRAP_VERSION = '%s-%s' % (BOOTSTRAP, VERSION)
SERVER_MODE = '%s-%s' % (SERVER, MODE)
GET = 'get'
SET = 'set'
LIST = 'list'
SCRIPT = 'script'
TEST = 'test'
UPGRADE = 'upgrade'
PROVISION = 'provision'
PROVISIONING = 'provisioning'
UNPROVISIONED = 'unprovisioned'
IDLE = 'idle'
PRODUCTION = 'production'
INVALID = 'invalid'
REPSITORY = 'repository'
STATUS = 'status'
UPGRADING = 'upgrading'
VALID = 'valid'
INVALID = 'invalid'
INVALID_PRODUCT = '%s-%s' % (INVALID, PRODUCT)
INVALID_KEY = '%s-%s' % (INVALID, KEY)
INVALID_VERSION = '%s-%s' % (INVALID, VERSION)
INVALID_TEST = '%s-%s' % (INVALID, TEST)
INVALID_MODE = '%s-%s' % (INVALID, MODE)
INVALID_SCRIPT = '%s-%s' % (INVALID, SCRIPT)
REQARGS = 'required command line parameters'
OPTARGS = 'optional command line parameters'
WRITABLE = 'writable'
STATIC = 'static'
DESC = 'description'
UPGRADE_SCRIPT = '%s-%s' % (UPGRADE, SCRIPT)
MODE_SCRIPT = '%s-%s' % (MODE, SCRIPT)


# Subcommands and options for cli mode
SUBCMDS = {
        '%s.%s' % (PRODUCT, SET): {
            DESC: 'sets the specified configuration value for the specified product',
            REQARGS: (PRODUCT, KEY, VALUE)},
        '%s.%s' % (PRODUCT, GET): {
            DESC: 'reports the specified configuration value for the specified product',
            REQARGS: (PRODUCT, KEY)},
        '%s.%s' % (PRODUCT, LIST): {
            DESC: 'lists the products present on this server along with their current versions (one per line)'},
        '%s.%s' % (PRODUCT, UPGRADE): {
            DESC: 'upgrades the specified product to the specified version',
            REQARGS: (PRODUCT, REVISION),
            OPTARGS: (CALLBACK, SPAWN)},
        '%s.%s' % (SERVER, GET): {
            DESC: 'reports the specified server value',
            REQARGS: (KEY,)},
        '%s.%s' % (SERVER, MODE): {
            DESC: 'gets or sets the mode of this server',
            OPTARGS: (MODE,)},
        '%s.%s' % (SERVER, PROVISION): {
            DESC: 'provisions this server',
            OPTARGS: (CALLBACK, SPAWN)},
        '%s.%s' % (SERVER, SET): {
            DESC: 'sets the specified server value',
            REQARGS: (KEY, VALUE)}}

OPTIONS = {
        PRODUCT: {
            DESC: 'product name'},
        KEY: {
            DESC: 'configuration key name'},
        VALUE: {
            DESC: 'configuration value'},
        CALLBACK: {
            DESC: 'a url which should be visited when the upgrade is complete'},
        SPAWN: {
            DESC: 'if true the bootstrap command spawns itself'},
        MODE: {
            DESC: 'the bootstrap-compatible server mode'},
        REVISION: {
            DESC: 'product revision'}}

# Server modes
MODES = {
        UNPROVISIONED: {
            DESC:'The initial mode of a server; indicates no products have been provisioned on it.'},
        IDLE: {
            DESC: 'Only critical OS services should be running; all product services are inactive.'},
        PRODUCTION: {
            DESC: 'All product services are active.'},
        INVALID: {
            DESC: 'The server is in an invalid state that likely requires manual intervention.'}}

# Error tags
ERROR_TAGS = (INVALID_KEY, INVALID_PRODUCT, INVALID_VERSION, INVALID_TEST, INVALID_MODE, INVALID_SCRIPT)

# Server values
BOOTSTRAP_VERSION = '%s-%s' % (BOOTSTRAP, VERSION)
SERVER_MODE = '%s-%s' % (SERVER, MODE)
SERVER_TYPE = '%s-%s' % (SERVER, TYPE)
SERVER_VALUES = {BOOTSTRAP_VERSION: {STATIC: True }, SERVER_TYPE: {STATIC: True }, SERVER_MODE: {WRITABLE: True}}

# Product values
PRODUCT_VALUES = {VERSION: {WRITABLE: True}, REPOSITORY: {WRITABLE: True}, UPGRADING: {STATIC: True, WRITABLE: True}, UPGRADE_SCRIPT: {STATIC: True}, MODE_SCRIPT: {STATIC: True}, STATUS: {}}

# Classes
class BootStrapException(Exception):
    def __init__(self, tag, messages):
        if tag not in ERROR_TAGS:
            raise Exception, "Unknown error tag: %s\n" % tag
        self.tag = tag
        self.messages = messages
    def __str__(self):
        return repr(self.tag)

class BootStrap(object):
    """Bootstrap"""
    def __init__(self, static_config_file=DEFAULT_CONFIG_FILE, static_config_dict=None):
        """init"""
        self.static_config_file = static_config_file
        self.static_config_dict = static_config_dict
        self.static_config = ConfigParser()
        self.static_config.read(self.static_config_file)
        self.__init_dynamic_config()
        self.server_values = SERVER_VALUES
        self.product_values = PRODUCT_VALUES
        self.__set_product_version_access()

    def __write_static(self):
        """ """
        fo = None
        try:
            fo = open(self.static_config_file, 'w')
            self.static_config.write(fo)
            fo.close()
        except Exception, error:
            if fo:
                fo.close()
            raise Exception, error

    def __init_dynamic_config(self):
        """Creates the initial structure for dynamic configuration"""
        if not os.path.exists(DYNAMIC_CONFIG):
            os.mkdir(DYNAMIC_CONFIG)
            os.mkdir('%s/%s' % (DYNAMIC_CONFIG, PRODUCTS))

    def __set_product_version_access(self):
        """ handle flipping version key to readonly based on the server mode"""
        dynamic_config = self.__dynamic_config
        product_values = self.product_values
        if dynamic_config[SERVER_MODE] != UNPROVISIONED:
            writable(product_values[VERSION], True)
        elif dynamic_config[SERVER_MODE] == UNPROVISIONED:
            writable(product_values[VERSION], False, True)

    @property
    def __dynamic_config(self):
        """Returns a dict representing the dyanmic config read from disk"""
        dynamic_config = {PRODUCTS: {}}
        dynamic_config[SERVER_MODE] = filestore('%s/%s' % (DYNAMIC_CONFIG, SERVER_MODE))
        if dynamic_config[SERVER_MODE] not in MODES:
            filestore('%s/%s' % (DYNAMIC_CONFIG, SERVER_MODE), UNPROVISIONED)
        for product in os.listdir('%s/%s' % (DYNAMIC_CONFIG, PRODUCTS)):
            product_path = '%s/%s/%s' % (DYNAMIC_CONFIG, PRODUCTS, product)
            product_repository = filestore('%s/%s' % (product_path, REPOSITORY))
            product_status = filestore('%s/%s' % (product_path, STATUS))
            product_version = filestore('%s/%s' % (product_path, VERSION))
            dynamic_config[PRODUCTS][product] = { VERSION: product_version, REPOSITORY: product_repository }
        return dynamic_config

    def server_get(self, key):
        """Returns a server key value"""
        if not self.static_config.has_option(BOOTSTRAP, key):
            raise BootStrapException(INVALID_KEY, key)
        return self.static_config.get(BOOTSTRAP, key).replace('\n', '')

    def server_set(self, key, value):
        """Sets a bootstrap server config value"""
        server_values = self.server_values
        if not self.static_config.has_option(BOOTSTRAP, key):
            raise BootStrapException(INVALID_KEY, key)
        if not server_values[key].has_key(WRITABLE):
            raise BootStrapException(INVALID_KEY, '%s is a readonly value' % key)
        self.static_config.set(BOOTSTRAP, key, value)
        self.__write_static()

    def server_provision(self, spawn=True, callback=None):
        """ """
        if spawn:
            args = [sys.executable, sys.argv[0], '%s.%s' % (SERVER, PROVISION), False]
            if callback:
                args.append(callback)
            os.spawnv(os.P_NOWAIT, sys.executable, args)
        else:
            dynamic_config = self.__dynamic_config
            mode_key = '%s/%s' % (DYNAMIC_CONFIG, SERVER_MODE)
            filestore(mode_key, PROVISIONING)
            for product in dynamic_config[PRODUCTS].keys():
                product_version = dynamic_config[PRODUCTS][product][VERSION]
                try:
                    self.product_upgrade(product, product_version)
                except Exception, error:
                    filestore(mode_key, INVALID)
                    if callback:
                        callback_url = '%s?status=%s&message=%s' % (callback, INVALID, str(error))
                        read_url(callback_url)
                    if isinstance(error, BootStrapException):
                        raise error
                    else:
                        raise Exception("Unhandled exception")
                    
            filestore(mode_key, IDLE)
            if callback:
                callback_url = '%s?status=%s' % (callback, IDLE)
                read_url(callback_url)
            self.__set_product_version_access()

    def server_mode(self, mode=None):
        """ """
        dynamic_config = self.__dynamic_config
        mode_key = '%s/%s' % (DYNAMIC_CONFIG, SERVER_MODE)
        if not mode:
            return dynamic_config[SERVER_MODE].replace('\n', '')
        elif not mode in MODES.keys():
            raise BootStrapException(INVALID_MODE, mode)
        filestore(mode_key, mode)
        outs = list()
        errors = list()
        invalid_script_exceptions = list()
        for section in self.static_config.sections():
            if section.startswith(PRODUCT) and self.static_config.has_option(section, MODE_SCRIPT):
                mode_script = self.static_config.get(section, MODE_SCRIPT)
                if not os.path.exists(mode_script):
                    invalid_script_exceptions.append(mode_script)
                    continue
                cmd = [mode_script,]
                if mode:
                    cmd.append(mode)
                out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
                if out:
                    out = out.splitlines()
                    outs.extend(out)
                if err:
                    err = err.splitlines()
                    errors.extend(err)
        if len(invalid_script_exceptions):
            raise BootStrapException(INVALID_SCRIPT, invalid_script_exceptions)

        return outs

    def product_get(self, product, key):
        """ """
        dynamic_config = self.__dynamic_config
        product_values = self.product_values
        section = product_section(product)
        if not product_values.has_key(key):
            raise BootStrapException(INVALID_KEY, key)
        if product_values[key].has_key(STATIC):
            if not self.static_config.has_section(section):
                raise BootStrapException(INVALID_PRODUCT, product)
            elif not self.static_config.has_option(section, key):
                raise BootStrapException(INVALID_KEY, key)
            return self.static_config.get(section, key).replace('\n', '')
        else:
            try:
                return dynamic_config[PRODUCTS][product][key]
            except KeyError:
                raise BootStrapException(INVALID_KEY, key)

    def product_set(self, product, key, value):
        """ """
        dynamic_config = self.__dynamic_config
        product_values = self.product_values
        section = product_section(product)
        if not self.static_config.has_section(section):
            raise BootStrapException(INVALID_PRODUCT, product)
        if not product_values[key].has_key(WRITABLE):
                raise BootStrapException(INVALID_KEY, '%s is a readonly value' % key)
        if product_values[key].has_key(STATIC):
            if not self.static_config.has_option(section, key):
                raise BootStrapException(INVALID_KEY, key)
            self.static_config.set(section, key, value)
        else:
            if not dynamic_config[PRODUCTS].has_key(product):
                os.mkdir('%s/%s/%s' % (DYNAMIC_CONFIG, PRODUCTS, product))
            filepath = '%s/%s/%s/%s' % (DYNAMIC_CONFIG, PRODUCTS, product, key)
            filestore(filepath, value)

    def product_list(self):
        """ """
        dynamic_config = self.__dynamic_config
        retval = ''
        if not len(dynamic_config[PRODUCTS].keys()):
            for section in self.static_config.sections():
                if section.startswith(PRODUCT):
                    retval += '%s\n' % section.split(':')[1].lstrip()
        else:                    
            for product in dynamic_config[PRODUCTS].keys():
                retval += '%s %s\n' % (product, dynamic_config[PRODUCTS][product][VERSION])
        retval = retval.rstrip('\n')
        return retval

    def product_test(self, product, test, callback=None):
        """ """

    def product_upgrade(self, product, version, spawn=True, callback=None):
        """ """
        if spawn:
            args = [sys.executable, sys.argv[0], '%s.%s' % (PRODUCT, UPGRADE), product, version, False]
            if callback:
                args.append(callback)
            os.spawnv(os.P_NOWAIT, sys.executable, args)
        else:
            dynamic_config = self.__dynamic_config
            section = product_section(product)
            mode_key = '%s/%s' % (DYNAMIC_CONFIG, SERVER_MODE)
            product_path = '%s/%s/%s' % (DYNAMIC_CONFIG, PRODUCTS, product)
            upgrade_script = self.static_config.get(section, UPGRADE_SCRIPT)
            filestore('%s/%s' % (product_path, STATUS), UPGRADING)
            if not os.path.exists(upgrade_script):
                raise BootStrapException(INVALID_SCRIPT, upgrade_script)
            repository = dynamic_config[PRODUCTS][product][REPOSITORY]
            cmd = [upgrade_script, repository, version]
            out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
            out = out.splitlines()
            if not err:
                status = VALID
            else:
                status = INVALID
                filestore(mode_key, INVALID)    
            filestore('%s/%s' % (product_path, STATUS), status)
            if callback:
                if status == VALID:
                    callback_url = '%s?product=%s&status=%s&version=%s' % (callback, product, status, version)
                elif status == INVALID:
                    callback_url = '%s?product=%s&status=%s&version=%s&message=%s' % (callback, product, status, version, str(err))
                read_url(callback_url)
            return out

# Utilities for bootstrap
def writable(d, disable=False, enable=False):
    ''' Handles returning True/False + setting/unsetting the writable key on values dicts'''
    if d.has_key(WRITABLE):
        if disable:
            del d[WRITABLE]
        else:
            return True
    elif enable:
        d[WRITABLE] = True

def read_url(url):
    """ """
    request = urllib2.Request(url)
    #request.add_header('X-LighthouseToken', YOUR_TOKEN)
    response = urllib2.urlopen(request)
    data = response.read()
    return data

def product_section(product):
    """ """
    return '%s: %s' % (PRODUCT, product)

def filestore(filepath, value=None, delete_on_null=False):
    """ Handle using a plain text file to store/retrieve values """
    """ If no file exists an empty one is created """
    if not os.path.exists(filepath):
        open(filepath, 'w').close()
    fo = None
    retval = None
    try:
        if value:
            fo = open(filepath, 'w')
            fo.write(str(value))
        else:
            fo = open(filepath, 'r')
            retval = fo.readline().replace('\n', '')
        fo.close()
    except Exception, error:
        if fo:
            fo.close()
        print 'Error: %s' % error
        raise Exception
    return retval

# Command line parsing
def print_bootstrap_help():
    """Print help for tool"""
    print '%s %s' % (SCRIPT_NAME, SCRIPT_VERSION)
    print DESCRIPTION
    print '\nUsage:'
    for key in SUBCMDS.keys():
        # need to find a better way to format the option text
        line = '  %s' % key
        if SUBCMDS[key].has_key(REQARGS):
            line = '%s %s' % (line, str(SUBCMDS[key][REQARGS]).replace(
                '(', '').replace(
                    ')', '').replace(
                        '\'', '').replace(',', ''))
        if SUBCMDS[key].has_key(OPTARGS):
            line = '%s %s' % (line, str(SUBCMDS[key][OPTARGS]).replace(
                '(', '[').replace(
                    ')', ']').replace(
                        '[\'', '[[').replace(
                            '\']', ']]').replace(
                                ' \'', '[').replace('\',', ']'))
        print '  %s\n%-20s %s' % (line, '', SUBCMDS[key][DESC])

def print_subcommand_args_help(subcommand, argtype=1):
    """Print help for subcommands"""
    cmdinfo = SUBCMDS[subcommand]
    if not argtype:
        print 'Error: %s subcommand requires no parameters' % subcommand
        return
    elif argtype == 1:
        print 'Error: %s subcommand requires %d parameter[s]' % (
                subcommand, len(cmdinfo[REQARGS]))
        print 'Required parameters:'
        for opt in cmdinfo[REQARGS]:
            print '  %-23s %s' % (opt, OPTIONS[opt][DESC])
    elif argtype == 2:
        print 'Error: %s subcommand can have %d optional parameter[s]' % (
                subcommand, len(cmdinfo[OPTARGS]))
        print 'Optional parameters:'
        for opt in cmdinfo[OPTARGS]:
            print '  %-23s %s' % (opt, OPTIONS[opt][DESC])

def cliparse():
    """Validate cli"""

    # Validate subcommand
    if (len(sys.argv[1:]) < 1 or sys.argv[1] not in SUBCMDS.keys()):
        print_bootstrap_help()
        sys.exit(1)

    # Check required params
    subcommand = sys.argv[1]
    cmdinfo = SUBCMDS[subcommand]
    optcount = len(sys.argv[2:])
    if cmdinfo.has_key(REQARGS):
        if optcount < len(cmdinfo[REQARGS]):
            print_subcommand_args_help(subcommand)
            sys.exit(1)
    elif optcount and not cmdinfo.has_key(REQARGS) and not cmdinfo.has_key(OPTARGS):
        print_subcommand_args_help(subcommand, 0)
        sys.exit(1)

    # Check optional params
    if cmdinfo.has_key(OPTARGS):
        if cmdinfo.has_key(REQARGS):
            pad = len(cmdinfo[REQARGS])
        else:
            pad = 0
        optcount = len(sys.argv[(2 + pad):])
        if optcount > len(cmdinfo[OPTARGS]):
            print_subcommand_args_help(subcommand, 2)
            sys.exit(1)

    return subcommand, sys.argv[2:]

def main():
    """Provides a python bootstrap cli tool"""
    subcommand, reqargs = cliparse()
    noun, verb = subcommand.split('.')
    bootstrap = BootStrap()
    bootstrap_func = getattr(bootstrap, '%s_%s' % (noun, verb))
    try:
        res = bootstrap_func(*reqargs)
        if isinstance(res, str):
            print res
        elif isinstance(res, list):
            for line in res:
                print line
    except BootStrapException, error:
        if isinstance(error.messages, list):
            for message in error.messages:
                sys.stderr.write('%s: %s' % (error.tag, message))
        elif isinstance(error.messages, str):
            sys.stderr.write('%s: %s' % (error.tag, error.messages))
        sys.exit(1)

if __name__ == '__main__':
    main()
