# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2002-2005 Juan David Ib��ez Palomar <jdavid@itaapy.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Import from the Standard Library
from distutils import core
from distutils.command.build_py import build_py
import os
import sys



def get_abspath(globals_namespace, local_path):
    """
    Returns the absolute path to the required file.
    """
    mname = globals_namespace['__name__']

    if mname == '__main__' or mname == '__init__':
        mpath = os.getcwd()
    else:
        module = sys.modules[mname]
        if hasattr(module, '__path__'):
            mpath = module.__path__[0]
        elif '.' in mname:
            mpath = sys.modules[mname[:mname.rfind('.')]].__path__[0]
        else:
            mpath = mname

    drive, mpath = os.path.splitdrive(mpath)
    mpath = drive + os.path.join(mpath, local_path)

    # Make it working with Windows. Internally we use always the "/".
    if os.path.sep == '\\':
        mpath = mpath.replace(os.path.sep, '/')

    return mpath



############################################################################
# XXX To be removed once distutils works again:
# http://sourceforge.net/tracker/index.php?func=detail&aid=1183712&group_id=5470&atid=305470
class build_py_fixed(build_py):

    def get_data_files(self):
        """Generate list of '(package,src_dir,build_dir,filenames)' tuples"""
        data = []
        if not self.packages:
            return data
        for package in self.packages:
            # Locate package source directory
            src_dir = self.get_package_dir(package)

            # Compute package build directory
            build_dir = os.path.join(*([self.build_lib] + package.split('.')))

            # Length of path to strip from found files
            if src_dir:
                plen = len(src_dir)+1
            else:
                plen = 0

            # Strip directory from globbed filenames
            filenames = [
                file[plen:] for file in self.find_data_files(package, src_dir)
                ]
            data.append((package, src_dir, build_dir, filenames))
        return data



############################################################################
# Our all powerful setup
############################################################################
def setup(description='', classifiers=[]):
    from __init__ import __version__
    try:
        from itools.resources import get_resource
        from handlers.config import Config
    except ImportError:
        # Are we trying to install itools?
        # XXX This is ugly, because Python does not support relative imports
        start_local_import()
        from resources import get_resource
        from handlers.config import Config
        end_local_import()

    config = Config(get_resource('setup.conf'))

    # Initialize variables
    package_name = config.get_value('name')
    packages = [package_name]
    package_data = {package_name: []}

    # The sub-packages
    if config.has_value('packages'):
        subpackages = config.get_value('packages').split()
        for subpackage_name in subpackages:
            packages.append('%s.%s' % (package_name, subpackage_name))

    # Write the manifest file if it does not exists
    if not os.path.exists('MANIFEST'):
        os.system('git-ls-files > MANIFEST')

    # The data files
    for line in open('MANIFEST').readlines():
        line = line.strip()
        # Python files are included by default
        if line.endswith('.py'):
            continue

        path = line.split('/')
        n = len(path)
        if n == 1:
            package_data[package_name].append(line)
        elif path[0] == 'locale':
            package_data[package_name].append(line)
        elif path[0] in subpackages:
            subpackage = '%s.%s' % (package_name, path[0])
            files = package_data.setdefault(subpackage, [])
            files.append(os.path.join(*path[1:]))

    # The scripts
    if config.has_value('scripts'):
        scripts = config.get_value('scripts').split()
        scripts = [ os.path.join(*['scripts', x]) for x in scripts ]
    else:
        scripts = []

    core.setup(name = package_name,
               version = __version__,
               # Metadata
               # XXX Broken distutils, "sdist" don't likes unicode strings,
               # and "register" don't likes normal strings.
               author = config.get_value('author_name'),
               author_email = config.get_value('author_email'),
               license = config.get_value('license'),
               url = config.get_value('url'),
               description = config.get_value('description'),
               long_description = description,
               classifiers = classifiers,
               # Packages
               package_dir = {package_name: ''},
               packages = packages,
               package_data = package_data,
               # Scripts
               scripts = scripts,
               # XXX broken distutils
               cmdclass={'build_py': build_py_fixed})



############################################################################
# XXX Work-around the fact that Python does not implements (yet) relative
# imports (see PEP 328).
############################################################################

pythons_import = __import__

def local_import(name, globals={}, locals={}, fromlist=[]):
    if name.startswith('itools.'):
        name = name[7:]
    return pythons_import(name, globals, locals, fromlist)


def start_local_import():
    __builtins__['__import__'] = local_import


def end_local_import():
    __builtins__['__import__'] = pythons_import
