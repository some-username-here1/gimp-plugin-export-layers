#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Automatic taking and processing screenshots of the plug-in dialog for
documentation purposes.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from export_layers import pygimplib as pg
from future.builtins import *

import os
import time

import pygtk
pygtk.require('2.0')
import gtk

import gimp
from gimp import pdb

from export_layers import builtin_procedures
from export_layers import builtin_constraints
from export_layers import actions
from export_layers import settings_main
from export_layers.gui import main as gui_main


PLUGINS_DIRPATH = os.path.dirname(os.path.dirname(pg.utils.get_current_module_filepath()))

TEST_IMAGES_DIRPATH = os.path.join(pg.config.PLUGIN_SUBDIRPATH, 'tests', 'test_images')
TEST_IMAGES_FILEPATH = os.path.join(
  TEST_IMAGES_DIRPATH, 'test_export_layers_contents.xcf')

if gimp.user_directory(4):
  OUTPUT_DIRPATH = os.path.join(gimp.user_directory(4), 'Loading Screens', 'Components')
else:
  OUTPUT_DIRPATH = os.path.join(gimp.directory, 'Loading Screens', 'Components')

SCREENSHOTS_DIRPATH = os.path.join(PLUGINS_DIRPATH, 'docs', 'images')
SCREENSHOT_DIALOG_BASIC_USAGE_FILENAME = 'screenshot_dialog_basic_usage.png'
SCREENSHOT_DIALOG_CUSTOMIZING_EXPORT_FILENAME = 'screenshot_dialog_customizing_export.png'


def take_screenshots(gui, dialog, settings):
  pg.path.make_dirs(OUTPUT_DIRPATH)
  
  settings['gui_session/current_directory'].set_value(OUTPUT_DIRPATH)
  settings['gui/show_more_settings'].set_value(False)
  
  decoration_offsets = move_dialog_to_corner(dialog, settings)
  
  gui.name_preview.set_selected_items(set([
    gui.name_preview.exporter.item_tree['main-background'].raw.ID]))
  
  dialog.set_focus(gui.name_preview.tree_view)
  
  while gtk.events_pending():
    gtk.main_iteration()
  
  take_and_process_screenshot(
    SCREENSHOTS_DIRPATH,
    SCREENSHOT_DIALOG_BASIC_USAGE_FILENAME,
    settings,
    decoration_offsets)
  
  settings['gui/show_more_settings'].set_value(True)
  
  actions.clear(settings['main/procedures'])
  actions.clear(settings['main/constraints'])
  
  actions.add(
    settings['main/procedures'],
    builtin_procedures.BUILTIN_PROCEDURES['insert_background_layers'])
  actions.reorder(
    settings['main/procedures'], 'insert_background_layers', 0)
  settings['main/procedures/added/use_layer_size/enabled'].set_value(False)
  
  actions.add(
    settings['main/constraints'],
    builtin_constraints.BUILTIN_CONSTRAINTS['only_layers_without_tags'])
  
  while gtk.events_pending():
    gtk.main_iteration()
  
  gui.name_preview.set_selected_items(set([
    gui.name_preview.exporter.item_tree['bottom-frame'].raw.ID]))
  
  while gtk.events_pending():
    gtk.main_iteration()
  
  take_and_process_screenshot(
    SCREENSHOTS_DIRPATH,
    SCREENSHOT_DIALOG_CUSTOMIZING_EXPORT_FILENAME,
    settings,
    decoration_offsets)
  
  gtk.main_quit()
  

def take_and_process_screenshot(
      screenshots_dirpath, filename, settings, decoration_offsets):
  #HACK: Wait a while until the window is fully shown.
  time.sleep(1)
  
  screenshot_image = take_screenshot()
  
  crop_to_dialog(screenshot_image, settings, decoration_offsets)
  
  pdb.gimp_file_save(
    screenshot_image,
    screenshot_image.active_layer,
    os.path.join(screenshots_dirpath, filename),
    filename)
  
  pdb.gimp_image_delete(screenshot_image)
  

def take_screenshot():
  return pdb.plug_in_screenshot(1, -1, 0, 0, 0, 0)


def move_dialog_to_corner(dialog, settings):
  settings['gui/dialog_position'].set_value((0, 0))
  dialog.set_gravity(gtk.gdk.GRAVITY_STATIC)
  decoration_offset_x, decoration_offset_y = dialog.get_position()
  dialog.set_gravity(gtk.gdk.GRAVITY_NORTH_WEST)
  settings['gui/dialog_position'].set_value((-decoration_offset_x, 0))
  
  return decoration_offset_x, decoration_offset_y


def crop_to_dialog(image, settings, decoration_offsets):
  settings['gui/dialog_size'].gui.update_setting_value()
  
  pdb.gimp_image_crop(
    image,
    settings['gui/dialog_size'].value[0],
    settings['gui/dialog_size'].value[1] + decoration_offsets[1],
    0,
    0)
  
  pdb.plug_in_autocrop(image, image.active_layer)


#===============================================================================


def main(settings=None):
  if not settings:
    settings = settings_main.create_settings()
  
  image = pdb.gimp_file_load(TEST_IMAGES_FILEPATH, os.path.basename(TEST_IMAGES_FILEPATH))
  
  layer_tree = pg.itemtree.LayerTree(image, name=pg.config.SOURCE_NAME, is_filtered=True)
  
  settings['special/image'].set_value(image)
  
  gui_main.ExportLayersDialog(layer_tree, settings, run_gui_func=take_screenshots)
  
  pdb.gimp_image_delete(image)
