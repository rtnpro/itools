# -*- coding: UTF-8 -*-
# Copyright (C) 2006-2011 J. David Ibáñez <jdavid.ibp@gmail.com>
# Copyright (C) 2009 David Versmisse <versmisse@lil.univ-littoral.fr>
# Copyright (C) 2009-2011 Hervé Cauwelier <herve@oursours.net>
# Copyright (C) 2010 Sylvain Taverne <taverne.sylvain@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the Standard Library
from distutils import core
from distutils.core import Extension
from distutils.command.build_ext import build_ext
from distutils.command.sdist import sdist
from distutils.errors import LinkError
from os import listdir
from os.path import exists, isfile, isdir, join as join_path
from re import compile
from sys import _getframe, argv

# Import from itools
from itools.core import freeze, get_pipe, get_version
from itools.handlers import ro_database
from git import open_worktree
from handlers import SetupConf



def make_version(cwd='.'):
    """This function finds out the version number from the source, this will
    be written to the 'version.txt' file, which will be read once the software
    is installed to get the version number.
    """
    worktree = open_worktree(cwd)
    # The name of the active branch
    branch = worktree.get_branch_name()
    if branch is None:
        return None

    # The tag
    description = worktree.git_describe()

    # The version name
    if description:
        tag, n, commit = description
        if tag.startswith(branch):
            version = tag
        else:
            version = '%s-%s' % (branch, tag)
        # Exact match
        if n == 0:
            return version
    else:
        version = branch

    # Get the timestamp
    head = worktree.get_metadata()
    timestamp = head['committer_date']
    timestamp = timestamp.strftime('%Y%m%d%H%M')
    return '%s-%s' % (version, timestamp)



def get_files(excluded_paths, filter=lambda x: True):
    for name in listdir('.'):
        if name in excluded_paths:
            continue

        if isdir(name):
            stack = [name]
            while stack:
                base = stack.pop()
                for name in listdir(base):
                    path = join_path(base, name)
                    if isdir(path):
                        stack.append(path)
                    elif filter(name):
                        yield path
        elif filter(name):
            yield name



class OptionalExtension(Extension):
    """An Optional Extension is a C extension that complements the package
    without being mandatory. It typically depends on external libraries. If the
    libraries are not available, the package will be installed without this
    extra module. Build errors will still be reported. Developers are
    responsible for testing the availability of the package, e.g. try/except
    ImportError.

    Simply Use OptionalExtension instead of Extension in your setup.
    """



class OptionalBuildExt(build_ext):
    """Internal class to support OptionalExtension.
    """

    def build_extension(self, ext):
        if not isinstance(ext, OptionalExtension):
            return build_ext.build_extension(self, ext)
        try:
            build_ext.build_extension(self, ext)
        except LinkError:
            print ""
            print "  '%s' module will not be available." % ext.name
            print "  Make sure the following libraries are installed:",
            print ", ".join(ext.libraries)
            print "  This error is not fatal, continuing build..."
            print ""



class FixedSdist(sdist):
    """Fixing sdist not reading the MANIFEST
    http://bugs.python.org/issue11104
    FIXME Remove this once issue 11104 is resolved, hopefully by Python 2.7.2
    """

    def get_file_list(self):
        """Figure out the list of files to include in the source
        distribution, and put it in 'self.filelist'.  This might involve
        reading the manifest template (and writing the manifest), or just
        reading the manifest, or just using the default file set -- it all
        depends on the user's options.
        """
        # new behavior when using a template:
        # the file list is recalculated everytime because
        # even if MANIFEST.in or setup.py are not changed
        # the user might have added some files in the tree that
        # need to be included.
        #
        #  This makes --force the default and only behavior with templates
        template_exists = isfile(self.template)
        manifest_exists = isfile(self.manifest)
        if not template_exists and manifest_exists:
                self.read_manifest()
                return
        if not template_exists:
            self.warn(("manifest template '%s' does not exist " +
                       "(using default file list)") %
                      self.template)
        self.filelist.findall()
        if self.use_defaults:
            self.add_defaults()
        if template_exists:
            self.read_template()
        if self.prune:
            self.prune_file_list()
        self.filelist.sort()
        self.filelist.remove_duplicates()
        self.write_manifest()



def get_compile_flags(command):
    include_dirs = []
    extra_compile_args = []
    library_dirs = []
    libraries = []

    if isinstance(command, str):
        command = command.split()
    data = get_pipe(command)

    for line in data.splitlines():
        for token in line.split():
            flag, value = token[:2], token[2:]
            if flag == '-I':
                include_dirs.append(value)
            elif flag == '-f':
                extra_compile_args.append(token)
            elif flag == '-L':
                library_dirs.append(value)
            elif flag == '-l':
                libraries.append(value)

    return {'include_dirs': include_dirs,
            'extra_compile_args': extra_compile_args,
            'library_dirs': library_dirs,
            'libraries': libraries}



def get_config():
    return ro_database.get_handler('setup.conf', SetupConf)



def get_manifest():
    worktree = open_worktree('.', soft=True)
    if worktree:
        exclude = frozenset(['.gitignore'])
        return [ x for x in worktree.get_filenames() if x not in exclude ]

    # No git: find out source files
    config = get_config()
    target_languages = config.get_value('target_languages')

    exclude = frozenset(['.git', 'build', 'dist'])
    bad_files = compile('.*(~|pyc|%s)$' % '|'.join(target_languages))
    return get_files(exclude, filter=lambda x: not bad_files.match(x))



def setup(ext_modules=freeze([])):
    mname = _getframe(1).f_globals.get('__name__')
    version = get_version(mname)

    config = get_config()

    # Initialize variables
    package_name = config.get_value('package_name')
    if package_name is None:
        package_name = config.get_value('name')
    packages = [package_name]
    package_data = {package_name: []}

    # The sub-packages
    if config.has_value('packages'):
        subpackages = config.get_value('packages')
        for subpackage_name in subpackages:
            packages.append('%s.%s' % (package_name, subpackage_name))
    else:
        subpackages = []

    # Write the manifest file if it does not exist
    if exists('MANIFEST'):
        filenames = [ x.strip() for x in open('MANIFEST').readlines() ]
    else:
        filenames = get_manifest()
        lines = [ x + '\n' for x in filenames ]
        open('MANIFEST', 'w').write(''.join(lines))

    # Python files are included by default
    filenames = [ x for x in filenames if not x.endswith('.py') ]

    # The data files
    for line in filenames:
        path = line.split('/')
        if path[0] in subpackages:
            subpackage = '%s.%s' % (package_name, path[0])
            files = package_data.setdefault(subpackage, [])
            files.append(join_path(*path[1:]))
        elif path[0] not in ('archive', 'docs', 'scripts', 'test'):
            package_data[package_name].append(line)

    # The scripts
    if config.has_value('scripts'):
        scripts = config.get_value('scripts')
        scripts = [ join_path(*['scripts', x]) for x in scripts ]
    else:
        scripts = []

    author_name = config.get_value('author_name')
    # XXX Workaround buggy distutils ("sdist" don't likes unicode strings,
    # and "register" don't likes normal strings).
    if 'register' in argv:
        author_name = unicode(author_name, 'utf-8')
    classifiers = [ x for x in config.get_value('classifiers') if x ]
    core.setup(name = package_name,
               version = version,
               # Metadata
               author = author_name,
               author_email = config.get_value('author_email'),
               license = config.get_value('license'),
               url = config.get_value('url'),
               description = config.get_value('title'),
               long_description = config.get_value('description'),
               classifiers = classifiers,
               # Packages
               package_dir = {package_name: '.'},
               packages = packages,
               package_data = package_data,
               # Requires / Provides
               requires = config.get_value('requires'),
               provides = config.get_value('provides'),
               # Scripts
               scripts = scripts,
               cmdclass = {
                   'build_ext': OptionalBuildExt,
                   'sdist': FixedSdist},
               # C extensions
               ext_modules=ext_modules)
