# -*- coding: UTF-8 -*-
# Copyright (C) 2006-2010 J. David Ibáñez <jdavid.ibp@gmail.com>
# Copyright (C) 2007 Nicolas Deram <nderam@gmail.com>
# Copyright (C) 2008 Gautier Hayoun <gautier.hayoun@supinfo.com>
# Copyright (C) 2008, 2010 David Versmisse <versmisse@lil.univ-littoral.fr>
# Copyright (C) 2010 Hervé Cauwelier <herve@oursours.net>
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
from unittest import TestCase, main

# Import from itools
from itools.handlers import ro_database
from itools.handlers import RWDatabase
from itools.handlers import TextFile, ConfigFile, TGZFile
from itools.fs import lfs


rw_database = RWDatabase(fs=lfs)


class StateTestCase(TestCase):

    def test_abort(self):
        handler = rw_database.get_handler('tests/hello.txt')
        self.assertEqual(handler.data, u'hello world\n')
        handler.set_data(u'bye world\n')
        self.assertEqual(handler.data, u'bye world\n')
        handler.abort_changes()
        self.assertEqual(handler.data, u'hello world\n')



class FolderTestCase(TestCase):

    def setUp(self):
        database = RWDatabase(100, 100)
        self.database = database
        self.root = database.get_handler('.')
        file = lfs.make_file('tests/toto.txt')
        try:
            file.write('I am Toto\n')
        finally:
            file.close()


    def tearDown(self):
        folder = lfs.open('tests')
        for name in 'toto.txt', 'fofo.txt', 'fofo2.txt', 'empty':
            if folder.exists(name):
                folder.remove(name)
        if lfs.exists("test_dir"):
            lfs.remove("test_dir")


    def test_remove(self):
        folder = self.root.get_handler('tests')
        folder.del_handler('toto.txt')
        self.assertEqual(lfs.exists('tests/toto.txt'), True)
        self.assertIsNone(folder.get_handler('toto.txt', soft=True))
        # Save
        self.database.save_changes()
        self.assertEqual(lfs.exists('tests/toto.txt'), False)
        self.assertIsNone(folder.get_handler('toto.txt', soft=True))


    def test_remove_add(self):
        folder = self.root.get_handler('tests')
        folder.del_handler('toto.txt')
        folder.set_handler('toto.txt', TextFile())
        self.assertEqual(lfs.exists('tests/toto.txt'), True)
        self.assertIsNotNone(folder.get_handler('toto.txt', soft=True))
        # Save
        self.database.save_changes()
        self.assertEqual(lfs.exists('tests/toto.txt'), True)
        self.assertIsNotNone(folder.get_handler('toto.txt', soft=True))


    def test_add_remove(self):
        database = self.database

        # Add a new file
        new_file = TextFile(data=u'New file\n')
        database.set_handler('test_dir/new_file.txt', new_file)

        # And suppress it
        database.del_handler('test_dir/new_file.txt')


    def test_remove_add_remove(self):
        folder = self.root.get_handler('tests')
        folder.del_handler('toto.txt')
        folder.set_handler('toto.txt', TextFile())
        folder.del_handler('toto.txt')
        self.assertEqual(lfs.exists('tests/toto.txt'), True)
        self.assertIsNone(folder.get_handler('toto.txt', soft=True))
        # Save
        self.database.save_changes()
        self.assertEqual(lfs.exists('tests/toto.txt'), False)
        self.assertIsNone(folder.get_handler('toto.txt', soft=True))


    def test_remove_remove(self):
        folder = self.root.get_handler('tests')
        folder.del_handler('toto.txt')
        self.assertRaises(Exception, folder.del_handler, 'toto.txt')


    def test_remove_add_add(self):
        folder = self.root.get_handler('tests')
        folder.del_handler('toto.txt')
        folder.set_handler('toto.txt', TextFile())
        self.assertRaises(Exception, folder.set_handler, 'toto.txt',
                          TextFile())


    def test_remove_abort(self):
        database = self.database
        folder = self.root.get_handler('tests')
        self.assertIsNotNone(folder.get_handler('toto.txt', soft=True))
        folder.del_handler('toto.txt')
        self.assertIsNone(folder.get_handler('toto.txt', soft=True))
        database.abort_changes()
        self.assertIsNotNone(folder.get_handler('toto.txt', soft=True))
        # Save
        database.save_changes()
        self.assertEqual(lfs.exists('tests/toto.txt'), True)


    def test_remove_folder(self):
        database = self.database

        # Add a new file
        new_file = TextFile(data=u'Hello world\n')
        database.set_handler('test_dir/hello.txt', new_file)

        # Suppress the directory
        database.del_handler('test_dir')

        # Try to get the file
        self.assertRaises(LookupError, database.get_handler,
                          'test_dir/hello.txt')


    def test_add_abort(self):
        database = self.database
        folder = self.root.get_handler('tests')
        self.assertIsNone(folder.get_handler('fofo.txt', soft=True))
        folder.set_handler('fofo.txt', TextFile())
        self.assertIsNotNone(folder.get_handler('fofo.txt', soft=True))
        database.abort_changes()
        self.assertIsNone(folder.get_handler('fofo.txt', soft=True))
        # Save
        database.save_changes()
        self.assertEqual(lfs.exists('tests/fofo.txt'), False)


    def test_add_copy(self):
        database = self.database
        folder = self.root.get_handler('tests')
        folder.set_handler('fofo.txt', TextFile())
        folder.copy_handler('fofo.txt', 'fofo2.txt')
        # Save
        database.save_changes()
        self.assertEqual(lfs.exists('tests/fofo2.txt'), True)


    def test_del_change(self):
        """Cannot change removed files.
        """
        folder = self.root.get_handler('tests')
        file = folder.get_handler('toto.txt')
        folder.del_handler('toto.txt')
        self.assertRaises(RuntimeError, file.set_data, u'Oh dear\n')


    def test_empty_folder(self):
        """Empty folders do not exist.
        """
        database = self.database
        root = self.root
        # Setup
        root.set_handler('tests/empty/sub/toto.txt', TextFile())
        database.save_changes()
        root.del_handler('tests/empty/sub/toto.txt')
        database.save_changes()
        self.assertEqual(lfs.exists('tests/empty'), True)
        # Test
        self.assertRaises(RuntimeError, root.set_handler, 'tests/empty',
                          TextFile())


    def test_not_empty_folder(self):
        """Empty folders do not exist.
        """
        database = self.database
        root = self.root
        # Setup
        root.set_handler('tests/empty/sub/toto.txt', TextFile())
        database.save_changes()
        # Test
        self.assertRaises(RuntimeError, root.set_handler, 'tests/empty',
                          TextFile())


    def test_add_get_handlers(self):
        database = self.database

        # Add a new file
        new_file = TextFile(data=u'Test get_handlers\n')
        database.set_handler('test_dir/test_get_handlers.txt', new_file)

        # get_handlers
        handlers = list(database.get_handlers("test_dir"))
        self.assertEqual(new_file in handlers, True)



class TextTestCase(TestCase):

    def test_load_file(self):
        handler = ro_database.get_handler('tests/hello.txt')
        self.assertEqual(handler.data, u'hello world\n')



class ConfigFileTestCase(TestCase):
    """ still need to complete the tests with schema """

    def setUp(self):
        self.config_path = "tests/setup.conf.test"
        if lfs.exists(self.config_path):
            lfs.remove(self.config_path)


    def tearDown(self):
        if lfs.exists(self.config_path):
            lfs.remove(self.config_path)


    def _init_test(self, value):
        # Init data
        if not lfs.exists(self.config_path):
            lfs.make_file(self.config_path)

        # Write data
        config = rw_database.get_handler(self.config_path, ConfigFile)
        config.set_value("test", value)
        config.save_state()


    def test_simple_value(self):
        # Init data
        value = "HELLO, WORLD!"
        self._init_test(value)

        # Read data
        config2 = rw_database.get_handler(self.config_path, ConfigFile)
        config2_value = config2.get_value("test")
        lfs.remove(self.config_path)

        # Test data
        self.assertEqual(config2_value, value)


    def test_long_value(self):
        # Init data
        value = "HELLO, WORLD!\n\nHELLO WORLD2222"
        self._init_test(value)

        # Read data
        config2 = rw_database.get_handler(self.config_path, ConfigFile)
        try:
            config2_value = config2.get_value("test")
        except SyntaxError, e:
            self.fail(e)
        finally:
            lfs.remove(self.config_path)

        # Test data
        self.assertEqual(config2_value, value)


    def test_last_line_empty(self):
        # Init data
        value = "HELLO, WORLD!\n\n"
        self._init_test(value)

        # Write data
        config = rw_database.get_handler(self.config_path, ConfigFile)
        config.set_value("test", value)
        config.save_state()

        # Read data
        config2 = rw_database.get_handler(self.config_path, ConfigFile)
        config2_value = config2.get_value("test")
        lfs.remove(self.config_path)

        # Test data
        self.assertEqual(config2_value, value)


    def test_quote_value(self):
        # Init data
        value = "HELLO, \"WORLD\"!"
        self._init_test(value)

        # Write data
        config = rw_database.get_handler(self.config_path, ConfigFile)
        try:
            config.set_value("test", value)
        except SyntaxError, e:
            self.fail(e)
        config.save_state()

        # Read data
        config2 = rw_database.get_handler(self.config_path, ConfigFile)
        try:
            config2_value = config2.get_value("test")
        except SyntaxError, e:
            self.fail(e)
        finally:
            lfs.remove(self.config_path)

        # Test data
        self.assertEqual(config2_value, value)



    def test_wrapped_quote_value(self):
        # Init data
        value = "\"HELLO, WORLD!\""
        self._init_test(value)

        # Write data
        config = rw_database.get_handler(self.config_path, ConfigFile)
        try:
            config.set_value("test", value)
        except SyntaxError, e:
            self.fail(e)
        config.save_state()

        # Read data
        config2 = ro_database.get_handler(self.config_path, ConfigFile)
        try:
            config2_value = config2.get_value("test")
        except SyntaxError, e:
            self.fail(e)
        finally:
            lfs.remove(self.config_path)

        # Test data
        self.assertEqual(config2_value, value)


###########################################################################
# Archive files
###########################################################################
class ArchiveTestCase(TestCase):

    def test_get_handler(self):
        cls = ro_database.get_handler_class('handlers/test.tar.gz')
        self.assertEqual(cls, TGZFile)

        file = ro_database.get_handler('handlers/test.tar.gz')
        self.assertEqual(file.__class__, TGZFile)



if __name__ == '__main__':
    main()
