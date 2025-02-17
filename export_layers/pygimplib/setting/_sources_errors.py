# -*- coding: utf-8 -*-

"""Exceptions used in `setting.sources` and `setting.persistor` modules."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

__all__ = [
  'SourceError',
  'SettingsNotFoundInSourceError',
  'SourceNotFoundError',
  'SourceReadError',
  'SourceInvalidFormatError',
  'SourceWriteError',
]


class SourceError(Exception):
  pass


class SettingsNotFoundInSourceError(SourceError):
  
  def __init__(self, message, settings_not_found=None):
    super().__init__(message)
    
    self.settings_not_found = settings_not_found if settings_not_found is not None else []


class SourceNotFoundError(SourceError):
  pass


class SourceReadError(SourceError):
  pass


class SourceInvalidFormatError(SourceError):
  pass


class SourceWriteError(SourceError):
  pass
