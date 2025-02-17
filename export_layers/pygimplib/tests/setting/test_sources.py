# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

import mock

from ... import utils as pgutils

from ...setting import settings as settings_
from ...setting import sources as sources_

from .. import stubs_gimp
from . import stubs_group


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
  new_callable=stubs_gimp.ShelfStub)
class TestSessionSource(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
    new=stubs_gimp.ShelfStub())
  def setUp(self):
    self.source_name = 'test_settings'
    self.source = sources_.SessionSource(self.source_name)
    self.settings = stubs_group.create_test_settings()
  
  def test_write(self, mock_session_source):
    self.settings['file_extension'].set_value('png')
    self.settings['only_visible_layers'].set_value(True)
    
    self.source.write(self.settings)
    
    self.assertEqual(
      sources_.gimpshelf.shelf[self.source_name][
        self.settings['file_extension'].get_path('root')],
      'png')
    self.assertEqual(
      sources_.gimpshelf.shelf[self.source_name][
        self.settings['only_visible_layers'].get_path('root')],
      True)
  
  def test_write_multiple_settings_separately(self, mock_session_source):
    self.settings['file_extension'].set_value('jpg')
    self.source.write([self.settings['file_extension']])
    self.settings['only_visible_layers'].set_value(True)
    
    self.source.write([self.settings['only_visible_layers']])
    self.source.read([self.settings['file_extension']])
    self.source.read([self.settings['only_visible_layers']])
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['only_visible_layers'].value, True)
  
  def test_read(self, mock_session_source):
    data = {}
    data[self.settings['file_extension'].get_path('root')] = 'png'
    data[self.settings['only_visible_layers'].get_path('root')] = True
    sources_.gimpshelf.shelf[self.source_name] = data
    
    self.source.read(
      [self.settings['file_extension'], self.settings['only_visible_layers']])
    
    self.assertEqual(self.settings['file_extension'].value, 'png')
    self.assertEqual(self.settings['only_visible_layers'].value, True)
  
  def test_read_settings_not_found(self, mock_session_source):
    self.source.write([self.settings['file_extension']])
    with self.assertRaises(sources_.SettingsNotFoundInSourceError):
      self.source.read(self.settings)
  
  def test_read_settings_invalid_format(self, mock_session_source):
    with mock.patch(
           pgutils.get_pygimplib_module_path()
           + '.setting.sources.gimpshelf.shelf') as temp_mock_session_source:
      temp_mock_session_source.__getitem__.side_effect = Exception
      
      with self.assertRaises(sources_.SourceInvalidFormatError):
        self.source.read(self.settings)
  
  def test_read_invalid_setting_value_set_to_default_value(self, mock_session_source):
    setting_with_invalid_value = settings_.IntSetting('int', default_value=-1)
    self.source.write([setting_with_invalid_value])
    
    setting = settings_.IntSetting('int', default_value=2, min_value=0)
    self.source.read([setting])
    
    self.assertEqual(setting.value, setting.default_value)
  
  def test_clear(self, mock_session_source):
    self.source.write(self.settings)
    self.source.clear()
    
    with self.assertRaises(sources_.SourceNotFoundError):
      self.source.read(self.settings)
  
  def test_has_data_with_no_data(self, mock_session_source):
    self.assertFalse(self.source.has_data())
  
  def test_has_data_with_data(self, mock_session_source):
    self.source.write([self.settings['file_extension']])
    self.assertTrue(self.source.has_data())


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimp',
  new_callable=stubs_gimp.GimpModuleStub)
class TestPersistentSource(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimp.directory',
    new='gimp_directory')
  def setUp(self):
    self.source_name = 'test_settings'
    self.source = sources_.PersistentSource(self.source_name)
    self.settings = stubs_group.create_test_settings()
  
  def test_write_read(self, mock_persistent_source):
    self.settings['file_extension'].set_value('jpg')
    self.settings['only_visible_layers'].set_value(True)
    
    self.source.write(self.settings)
    self.source.read(self.settings)
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['only_visible_layers'].value, True)
  
  def test_write_multiple_settings_separately(self, mock_persistent_source):
    self.settings['file_extension'].set_value('jpg')
    self.source.write([self.settings['file_extension']])
    self.settings['only_visible_layers'].set_value(True)
    
    self.source.write([self.settings['only_visible_layers']])
    self.source.read([self.settings['file_extension']])
    self.source.read([self.settings['only_visible_layers']])
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['only_visible_layers'].value, True)
  
  def test_write_read_same_setting_name_in_different_groups(self, mock_persistent_source):
    settings = stubs_group.create_test_settings_hierarchical()
    file_extension_advanced_setting = settings_.FileExtensionSetting(
      'file_extension', default_value='png')
    settings['advanced'].add([file_extension_advanced_setting])
    
    self.source.write(settings.walk())
    self.source.read(settings.walk())
    
    self.assertEqual(settings['main/file_extension'].value, 'bmp')
    self.assertEqual(settings['advanced/file_extension'].value, 'png')
  
  def test_read_source_not_found(self, mock_persistent_source):
    with self.assertRaises(sources_.SourceNotFoundError):
      self.source.read(self.settings)
  
  def test_read_settings_not_found(self, mock_persistent_source):
    self.source.write([self.settings['file_extension']])
    with self.assertRaises(sources_.SettingsNotFoundInSourceError):
      self.source.read(self.settings)
  
  def test_read_settings_invalid_format(self, mock_persistent_source):
    self.source.write(self.settings)
    
    # Simulate formatting error
    parasite = sources_.gimp.parasite_find(self.source_name)
    parasite.data = parasite.data[:-1]
    sources_.gimp.parasite_attach(parasite)
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read(self.settings)
  
  def test_read_invalid_setting_value_set_to_default_value(self, mock_persistent_source):
    setting_with_invalid_value = settings_.IntSetting('int', default_value=-1)
    self.source.write([setting_with_invalid_value])
    
    setting = settings_.IntSetting('int', default_value=2, min_value=0)
    self.source.read([setting])
    
    self.assertEqual(setting.value, setting.default_value)
  
  def test_clear(self, mock_persistent_source):
    self.source.write(self.settings)
    self.source.clear()
    
    with self.assertRaises(sources_.SourceNotFoundError):
      self.source.read(self.settings)
  
  def test_has_data_with_no_data(self, mock_persistent_source):
    self.assertFalse(self.source.has_data())
  
  def test_has_data_with_data(self, mock_persistent_source):
    self.source.write([self.settings['file_extension']])
    self.assertTrue(self.source.has_data())


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimp',
  new_callable=stubs_gimp.GimpModuleStub)
class TestSourceReadWriteDict(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimp.directory',
    new='gimp_directory')
  def setUp(self):
    self.source_name = 'test_settings'
    self.source_session = sources_.SessionSource(self.source_name)
    self.source_persistent = sources_.PersistentSource(self.source_name)
    self.settings = stubs_group.create_test_settings()
  
  def test_read_dict(self, mock_persistent_source, mock_session_source):
    for source in [self.source_session, self.source_persistent]:
      self._test_read_dict(source)
  
  def test_read_dict_nonexistent_source(
        self, mock_persistent_source, mock_session_source):
    for source in [self.source_session, self.source_persistent]:
      self._test_read_dict_nonexistent_source(source)
  
  def test_write_dict(self, mock_persistent_source, mock_session_source):
    for source in [self.source_session, self.source_persistent]:
      self._test_write_dict(source)
  
  def _test_read_dict(self, source):
    source.write(self.settings)
    
    data_dict = source.read_dict()
    self.assertDictEqual(
      data_dict,
      {
        'file_extension': self.settings['file_extension'].value,
        'only_visible_layers': self.settings['only_visible_layers'].value,
        'overwrite_mode': self.settings['overwrite_mode'].value,
      })
  
  def _test_read_dict_nonexistent_source(self, source):
    self.assertIsNone(source.read_dict())
  
  def _test_write_dict(self, source):
    data_dict = {
      'file_extension': self.settings['file_extension'].default_value,
      'only_visible_layers': self.settings['only_visible_layers'].default_value,
    }
    
    self.settings['file_extension'].set_value('jpg')
    self.settings['only_visible_layers'].set_value(True)
    
    source.write_dict(data_dict)
    
    source.read(
      [self.settings['file_extension'], self.settings['only_visible_layers']])
    
    self.assertEqual(
      self.settings['file_extension'].value,
      self.settings['file_extension'].default_value)
    self.assertEqual(
      self.settings['only_visible_layers'].value,
      self.settings['only_visible_layers'].default_value)
