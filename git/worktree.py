# -*- coding: UTF-8 -*-
# Copyright (C) 2007, 2009, 2011-2012 J. David Ibáñez <jdavid.ibp@gmail.com>
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
from datetime import datetime
from os import listdir, makedirs, remove, rmdir, walk
from os.path import abspath, dirname, exists, getmtime, isabs, isdir, isfile
from os.path import normpath
from re import search
from shutil import copy2, copytree
from subprocess import Popen, PIPE
import time

# Import from pygit2
from pygit2 import Repository, Signature, GitError, init_repository
from pygit2 import GIT_SORT_REVERSE, GIT_SORT_TIME, GIT_OBJ_TREE
from pygit2 import GIT_STATUS_WT_MODIFIED, GIT_STATUS_WT_DELETED

# Import from itools
from itools.core import lazy


def message_short(commit):
    """Helper function to get the subject line of the commit message.

    XXX This code is based on the 'message_short' value that was once
    available in libgit2 (and removed by 5ae2f0c0135). It should be removed
    once libgit2 gets the feature back, see issue #250 for the discussion:

      https://github.com/libgit2/libgit2/pull/250
    """
    message = commit.message
    message = message.split('\n\n')[0]
    message = message.replace('\n', ' ')
    return message.rstrip()


def make_parent_dirs(path):
    folder = dirname(path)
    if not exists(folder):
        makedirs(folder)



class Worktree(object):

    def __init__(self, path, repo):
        self.path = abspath(path) + '/'
        self.repo = repo
        self.cache = {} # {sha: object}
        # FIXME These two fields are already available by libgit2. TODO
        # expose them through pygit2 and use them here.
        self.index_path = '%s/.git/index' % path
        self.index_mtime = None


    #######################################################################
    # Internal utility functions
    #######################################################################
    def _get_abspath(self, path):
        """Return the absolute version of the given path. This will be used by
        calls to the operating system, this way the code does not require the
        working directory to be set to the working tree.
        """
        if isabs(path):
            if path.startswith(self.path):
                return path
            raise ValueError, 'unexpected absolute path "%s"' % path
        if path == '.':
            return self.path
        return '%s%s' % (self.path, path)


    def _call(self, command):
        """Interface to cal git.git for functions not yet implemented using
        libgit2.
        """
        popen = Popen(command, stdout=PIPE, stderr=PIPE, cwd=self.path)
        stdoutdata, stderrdata = popen.communicate()
        if popen.returncode != 0:
            raise EnvironmentError, (popen.returncode, stderrdata)
        return stdoutdata


    def _resolve_reference(self, reference):
        """This method returns the SHA the given reference points to. For now
        only HEAD is supported.

        FIXME This is quick & dirty. TODO Implement references in pygit2 and
        use them here.
        """
        # Case 1: SHA
        if len(reference) == 40:
            return reference

        # Case 2: reference
        reference = self.repo.lookup_reference(reference)
        try:
            reference = reference.resolve()
        except KeyError:
            return None

        return reference.oid


    #######################################################################
    # External API
    #######################################################################
    def walk(self, path='.'):
        """This utility method traverses the working tree starting at the
        given path, it yields relative paths from the working tree, where
        folders end by '/' to distigish them from files.  The '.git' folder
        at the root is excluded from the traversal.

        FIXME The '/' trick will not work on Windows.
        TODO Idea: change the prototype to accept two callbacks, one for
        folders and another for files, instead of yielding the values.  These
        callbacks will be applied with a partial order: 'a' before 'b' if 'b'
        is a directory that contains 'a'. This will work on Windows and would
        allow us to rewrite 'git rm' (but will it work for 'git status'?).
        """
        # 1. Check and normalize path
        if isabs(path):
            raise ValueError, 'unexpected absolute path "%s"' % path

        path = normpath(path)
        if path == '.':
            path = ''
        elif path == '.git':
            raise ValueError, 'cannot walk .git'
        elif not isdir('%s%s' % (self.path, path)):
            yield path
            return
        else:
            path += '/'

        # 2. Go
        stack = [path]
        while stack:
            folder_rel = stack.pop()
            folder_abs = '%s%s' % (self.path, folder_rel)
            for name in listdir(folder_abs):
                path_abs = '%s%s' % (folder_abs, name)
                path_rel = '%s%s' % (folder_rel, name)
                if path_rel == '.git':
                    continue
                if isdir(path_abs):
                    path_rel += '/'
                    stack.append(path_rel)

                yield path_rel


    def lookup(self, sha):
        """Return the object by the given SHA. We use a cache to warrant that
        two calls with the same SHA will resolve to the same object, so the
        'is' operator will work.
        """
        cache = self.cache
        if sha not in cache:
            cache[sha] = self.repo[sha]

        return cache[sha]


    def lookup_from_commit_by_path(self, commit, path):
        """Return the object (tree or blob) the given path points to from the
        given commit, or None if the given path does not exist.

        TODO Implement Tree.getitem_by_path(path) => TreeEntry in pygit2 to
        speed up things.
        """
        obj = commit.tree
        for name in path.split('/'):
            if obj.type != GIT_OBJ_TREE:
                return None

            if name not in obj:
                return None
            entry = obj[name]
            obj = self.lookup(entry.oid)
        return obj


    @property
    def index(self):
        """Gives access to the index file. Reloads the index file if it has
        been modified in the filesystem.

        TODO An error condition should be raised if the index file has
        been modified both in the filesystem and in memory.
        """
        index = self.repo.index
        # Bare repository
        if index is None:
            raise RuntimeError, 'expected standard repository, not bare'

        path = self.index_path
        if exists(path):
            mtime = getmtime(path)
            if not self.index_mtime or self.index_mtime < mtime:
                index.read()
                self.index_mtime = mtime

        return index


    def update_tree_cache(self):
        """libgit2 is able to read the tree cache, but not to write it.
        To speed up 'git_commit' this method should be called from time to
        time, it updates the tree cache by calling 'git write-tree'.
        """
        command = ['git', 'write-tree']
        self._call(command)


    def git_add(self, *args):
        """Equivalent 'git add', adds the given paths to the index file.
        If a path is a folder, adds all its content recursively.
        """
        index = self.index
        for path in args:
            for path in self.walk(path):
                if path[-1] != '/':
                    index.add(path)


    def git_rm(self, *args):
        """Equivalent to 'git rm', removes the given paths from the index
        file and from the filesystem. If a path is a folder removes all
        its content recursively, files and folders.
        """
        index = self.index
        n = len(self.path)
        for path in args:
            abspath = self._get_abspath(path)
            # 1. File
            if isfile(abspath):
                del index[path]
                remove(abspath)
                continue
            # 2. Folder
            for root, dirs, files in walk(abspath, topdown=False):
                for name in files:
                    del index['%s/%s' % (root[n:], name)]
                    remove('%s/%s' % (root, name))
                for name in dirs:
                    rmdir('%s/%s' % (root, name))


    def git_mv(self, source, target, add=True):
        """Equivalent to 'git mv': moves the file or folder in the filesystem
        from 'source' to 'target', removes the source from the index file,
        and adds the target to the index file.

        NOTE If the boolean parameter 'add' is set to False then the target
        files will not be added to the index file (this feature is used by
        itools.database). TODO Check whether we cannot change itools.database
        so we can remove this parameter.
        """
        source_abs = self._get_abspath(source)
        target = self._get_abspath(target)
        # 1. Copy
        if isfile(source_abs):
            make_parent_dirs(target)
            copy2(source_abs, target)
        else:
            copytree(source_abs, target)

        # 2. Git rm
        self.git_rm(source)

        # 3. Git add
        if add is True:
            self.git_add(target)


    def git_clean(self):
        """Equivalent to 'git clean -fxd', removes all files from the working
        tree that are not in the files, and removes the empty folders too.
        """
        index = self.index

        walk = self.walk()
        for path in sorted(walk, reverse=True):
            abspath = '%s%s' % (self.path, path)
            if path[-1] == '/':
                if not listdir(abspath):
                    rmdir(abspath)
            elif path not in index:
                remove(abspath)


    @lazy
    def username(self):
        cmd = ['git', 'config', '--get', 'user.name']
        return self._call(cmd).rstrip()


    @lazy
    def useremail(self):
        cmd = ['git', 'config', '--get', 'user.email']
        return self._call(cmd).rstrip()


    def git_commit(self, message, author=None, date=None):
        """Equivalent to 'git commit', we must give the message and we can
        also give the author and date.
        """
        from calendar import timegm

        # TODO Check the 'nothing to commit' case

        # Write index
        self.index.write()
        self.index_mtime = getmtime(self.index_path)

        # Tree
        tree = self.index.write_tree()

        # Parent
        parent = self._resolve_reference('HEAD')
        parents = [parent] if parent else []

        # Committer
        when_time = time.time()
        when_offset = - (time.altzone if time.daylight else time.timezone)
        when_offset = when_offset / 60

        name = self.username
        email = self.useremail
        committer = Signature(name, email, when_time, when_offset)

        # Author
        if author is None:
            author = (name, email)

        if date:
            if date.tzinfo:
                from pytz import utc
                when_time = date.astimezone(utc)            # To UTC
                when_time = when_time.timetuple()           # As struct_time
                when_time = timegm(when_time)               # To unix time
                when_offset = date.utcoffset().seconds / 60
            else:
                err = "Worktree.git_commit doesn't support naive datatime yet"
                raise NotImplementedError, err

        author = Signature(author[0], author[1], when_time, when_offset)

        # Create the commit
        return self.repo.create_commit('HEAD', author, committer, message,
                                       tree, parents)


    def git_log(self, paths=None, n=None, author=None, grep=None,
                reverse=False, reference='HEAD'):
        """Equivalent to 'git log', optional keyword parameters are:

          paths   -- return only commits where the given paths have been
                     changed
          n       -- show at most the given number of commits
          author  -- filter out commits whose author does not match the given
                     pattern
          grep    -- filter out commits whose message does not match the
                     given pattern
          reverse -- return results in reverse order
        """
        # Get the sha
        sha = self._resolve_reference(reference)

        # Sort
        sort = GIT_SORT_TIME
        if reverse is True:
            sort |= GIT_SORT_REVERSE

        # Go
        commits = []
        for commit in self.repo.walk(sha, GIT_SORT_TIME):
            # --author=<pattern>
            if author:
                commit_author = commit.author
                if not search(author, commit_author.name) and \
                   not search(author, commit_author.email):
                    continue

            # --grep=<pattern>
            if grep:
                if not search(grep, commit.message):
                    continue

            # -- path ...
            if paths:
                parents = commit.parents
                parent = parents[0] if parents else None
                for path in paths:
                    a = self.lookup_from_commit_by_path(commit, path)
                    if parent is None:
                        if a:
                            break
                    else:
                        b = self.lookup_from_commit_by_path(parent, path)
                        if a is not b:
                            break
                else:
                    continue

            ts = commit.commit_time
            commits.append(
                {'sha': commit.hex,
                 'author_name': commit.author.name,
                 'author_date': datetime.fromtimestamp(ts),
                 'message_short': message_short(commit)})
            if n is not None:
                n -= 1
                if n == 0:
                    break

        # Ok
        return commits


    def git_reset(self):
        """Equivalent to 'git reset --hard -q', this method restores the
        state of the working tree and index file to match the state of the
        latest commit.
        """
        # (1) Read tree
        head = self._resolve_reference('HEAD')
        tree_oid = self.lookup(head).tree.oid
        index = self.index
        index.read_tree(tree_oid)
        index.write()

        # (2) Checkout tree
        repo = self.repo
        for entry in index:
            path = entry.path
            status = repo.status_file(path)
            if status & (GIT_STATUS_WT_MODIFIED | GIT_STATUS_WT_DELETED):
                # Checkout
                data = self.lookup(index[path].oid).data
                path = self._get_abspath(path)
                make_parent_dirs(path)
                with open(path, 'w') as f:
                    f.write(data)


    def git_diff(self, since, until=None, paths=None):
        """Return the diff between two commits, eventually reduced to the
        given paths.

        TODO Implement using Python's difflib standard library, to avoid
        calling Git.
        """
        if until is None:
            data = self._call(['git', 'show', since, '--pretty=format:'])
            return data[1:]

        cmd = ['git', 'diff', '%s..%s' % (since, until)]
        if paths:
            cmd.append('--')
            cmd.extend(paths)
        return self._call(cmd)


    def git_stats(self, since, until=None, paths=None):
        """Return statistics of the changes done between two commits,
        eventually reduced to the given paths.

        TODO Implement using libgit2
        """
        if until is None:
            cmd = ['git', 'show', '--pretty=format:', '--stat', since]
            data = self._call(cmd)
            return data[1:]

        cmd = ['git', 'diff', '--stat', '%s..%s' % (since, until)]
        if paths:
            cmd.append('--')
            cmd.extend(paths)
        return self._call(cmd)


    def git_describe(self):
        """Equivalent to 'git describe', returns a unique but short
        identifier for the current commit based on tags.

        TODO Implement using libgit2
        """
        # Call
        command = ['git', 'describe', '--tags', '--long']
        try:
            data = self._call(command)
        except EnvironmentError:
            return None

        # Parse
        tag, n, commit = data.rsplit('-', 2)
        return tag, int(n), commit


    def get_branch_name(self):
        """Returns the name of the current branch.
        """
        ref = open('%s/.git/HEAD' % self.path).read().rstrip()
        ref = ref.rsplit('/', 1)
        return ref[1] if len(ref) == 2 else None


    def get_filenames(self):
        """Returns the list of filenames tracked by git.
        """
        index = self.index
        return [ index[i].path for i in range(len(index)) ]


    def get_files_changed(self, since, until):
        """Return the files that have been changed between two commits.

        TODO Implement with libgit2
        """
        expr = '%s..%s' % (since, until)
        cmd = ['git', 'show', '--numstat', '--pretty=format:', expr]
        data = self._call(cmd)
        lines = data.splitlines()
        return frozenset([ line.split('\t')[-1] for line in lines if line ])


    def get_metadata(self, reference='HEAD'):
        """Resolves the given reference and returns metadata information
        about the commit in the form of a dict.
        """
        sha = self._resolve_reference(reference)
        commit = self.lookup(sha)
        parents = commit.parents
        author = commit.author
        committer = commit.committer

        # TODO Use the offset for the author/committer time
        return {
            'tree': commit.tree.hex,
            'parent': parents[0].hex if parents else None,
            'author_name': author.name,
            'author_email': author.email,
            'author_date': datetime.fromtimestamp(author.time),
            'committer_name': committer.name,
            'committer_email': committer.email,
            'committer_date': datetime.fromtimestamp(committer.time),
            'message': commit.message,
            'message_short': message_short(commit),
            }



def open_worktree(path, init=False, soft=False):
    try:
        if init:
            repo = init_repository(path, False)
        else:
            repo = Repository('%s/.git' % path)
    except GitError:
        if soft:
            return None
        raise

    return Worktree(path, repo)
