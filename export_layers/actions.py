# -*- coding: utf-8 -*-

"""Creation and management of plug-in actions - procedures and constraints.

Most functions take a setting group containing actions as its first argument.

Many functions define events invoked on the setting group containing actions.
These events include:

* `'before-add-action'` - invoked when:
  * calling `add()` before adding an action,
  * calling `setting.Group.load()` or `setting.Persistor.load()` before loading
    an action (loading an action counts as adding),
  * calling `clear()` before resetting actions (due to initial actions
    being added back).
  
  Arguments: action dictionary to be added

* `'after-add-action'` - invoked when:
  * calling `add()` after adding an action,
  * calling `setting.Group.load()` or `setting.Persistor.load()` after loading
    an action (loading an action counts as adding),
  * calling `clear()` after resetting actions (due to initial actions
    being added back).
  
  Arguments: created action, original action dictionary (same as in
  `'before-add-action'`)

* `'before-reorder-action'` - invoked when calling `reorder()` before
  reordering an action.
  
  Arguments: action, position before reordering

* `'after-reorder-action'` - invoked when calling `reorder()` after reordering
  an action.
  
  Arguments: action, position before reordering, new position

* `'before-remove-action'` - invoked when calling `remove()` before removing an
  action.
  
  Arguments: action to be removed

* `'after-remove-action'` - invoked when calling `remove()` after removing an
  action.
  
  Arguments: name of the removed action

* `'before-clear-actions'` - invoked when calling `clear()` before clearing
  actions.

* `'after-clear-actions'` - invoked when calling `clear()` after clearing
  actions.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import gimpenums

from export_layers import pygimplib as pg

from export_layers import placeholders


BUILTIN_TAGS = {
  'background': _('Background'),
  'foreground': _('Foreground'),
}

DEFAULT_PROCEDURES_GROUP = 'default_procedures'
DEFAULT_CONSTRAINTS_GROUP = 'default_constraints'

_DEFAULT_ACTION_TYPE = 'procedure'
_REQUIRED_ACTION_FIELDS = ['name']


def create(name, initial_actions=None):
  """
  Create a `setting.Group` instance containing actions.
  
  Parameters:
  * `name` - name of the `setting.Group` instance.
  * `initial_actions` - list of dictionaries describing actions to be
    added by default. Calling `clear()` will reset the actions returned by
    this function to the initial actions. By default, no initial actions
    are added.
  
  The resulting `setting.Group` instance contains the following subgroups:
  * `'added'` - Contains actions added via `add()` or created in this
    function via `initial_actions` dictionary.
  * `'_added_data'` - Actions stored as dictionaries, used when loading or
    saving actions persistently. As indicated by the leading underscore, this
    subgroup is only for internal use and should not be modified outside
    `actions`.
  * `'_added_data_values'` - Values of actions stored as dictionaries, used
    when loading or saving actions persistently. As indicated by the leading
    underscore, this subgroup is only for internal use and should not be
    modified outside `actions`.
  
  Each created action in the returned group is a nested `setting.Group`. Each
  action contains the following settings or subgroups:
  * `'function'` - The function to call.
  * `'arguments'` - Arguments to `'function'` as a `setting.Group` instance
    containing arguments as separate `Setting` instances.
  * `'enabled'` - Whether the action should be applied or not.
  * `'display_name'` - The display name (human-readable name) of the action.
  * `'action_group'` - List of groups the action belongs to, used in
    `pygimplib.invoker.Invoker` and `exportlayers.LayerExporter`.
  * `'orig_name'` - The original name of the action. If an action with the
    same `'name'` field (see below) was previously added, the name of the new
    action is made unique to allow lookup of both actions. Otherwise,
    `'orig_name'` is equal to `'name'`.
  
  Each dictionary in the `initial_actions` list may contain the following
  fields:
  * `'name'` - This field is required. This is the `name` attribute of the
    created action.
  * `'type'` - Action type. See below for details.
  * `'function'` - The function to call.
  * `'arguments'` - Specified as list of dictionaries defining settings. Each
    dictionary must contain required attributes and can contain optional
    attributes as stated in `setting.Group.add()`.
  * `'enabled'`
  * `'display_name'`
  * `'action_group'`
  
  Depending on the specified `'type'`, the dictionary may contain additional
  fields and `create` may generate additional settings.
  
  Allowed values for `'type'`:
  * `'procedure'` (default) - Represents a procedure. `'action_group'`
    defaults to `DEFAULT_PROCEDURES_GROUP` if not defined.
  * `'constraint'` - Represents a constraint. `'action_group'` defaults to
    `DEFAULT_CONSTRAINTS_GROUP` if not defined.
  
  Additional allowed fields for type `'constraint'` include:
  * `'subfilter'` - The name of a nested filter for an `ObjectFilter` instance
    where constraints should be added. By default, `'subfilter'` is `None` (no
    nested filter is assumed).
  
  Custom fields are accepted as well. For each field, a separate setting is
  created, using the field name as the setting name.
  
  Raises:
  * `ValueError` - invalid `'type'` or missing required fields in
    `initial_actions`.
  """
  actions = pg.setting.Group(
    name=name,
    setting_attributes={
      'pdb_type': None,
      'setting_sources': None,
    })
  
  added_actions = pg.setting.Group(
    name='added',
    setting_attributes={
      'pdb_type': None,
      'setting_sources': None,
    })
  
  actions.add([
    added_actions,
    {
      'type': pg.SettingTypes.generic,
      'name': '_added_data',
      'default_value': _get_initial_added_data(initial_actions),
      'setting_sources': [pg.config.SESSION_SOURCE, pg.config.PERSISTENT_SOURCE]
    },
    {
      'type': pg.SettingTypes.generic,
      'name': '_added_data_values',
      'default_value': {},
      'setting_sources': [pg.config.SESSION_SOURCE, pg.config.PERSISTENT_SOURCE]
    },
  ])
  
  _create_actions_from_added_data(actions)
  
  actions.connect_event(
    'after-clear-actions',
    _create_actions_from_added_data)
  
  actions['_added_data'].connect_event(
    'before-load',
    _clear_actions_before_load_without_adding_initial_actions,
    actions)
  
  actions['_added_data'].connect_event(
    'after-load',
    lambda added_data_setting: (
      _create_actions_from_added_data(added_data_setting.parent)))
  
  actions['_added_data_values'].connect_event(
    'before-save',
    _get_values_from_actions,
    actions['added'])
  
  actions['_added_data_values'].connect_event(
    'after-load',
    _set_values_for_actions,
    actions['added'])
  
  return actions


def _get_initial_added_data(initial_actions):
  if not initial_actions:
    return []
  else:
    return [dict(action_dict) for action_dict in initial_actions]


def _clear_actions_before_load_without_adding_initial_actions(
      added_data_setting, actions_group):
  _clear(actions_group)


def _create_actions_from_added_data(actions):
  for action_dict in actions['_added_data'].value:
    actions.invoke_event('before-add-action', action_dict)
    
    action = _create_action_by_type(**dict(action_dict))
    actions['added'].add([action])
    
    actions.invoke_event('after-add-action', action, action_dict)


def _create_action_by_type(**kwargs):
  type_ = kwargs.pop('type', _DEFAULT_ACTION_TYPE)
  
  if type_ not in _ACTION_TYPES_AND_FUNCTIONS:
    raise ValueError(
      'invalid type "{}"; valid values: {}'.format(
        type_, list(_ACTION_TYPES_AND_FUNCTIONS)))
  
  for required_field in _REQUIRED_ACTION_FIELDS:
    if required_field not in kwargs:
      raise ValueError('missing required field: "{}"'.format(required_field))
  
  return _ACTION_TYPES_AND_FUNCTIONS[type_](**kwargs)


def _get_values_from_actions(added_data_values_setting, added_actions_group):
  added_data_values_setting.reset()
  
  for setting in added_actions_group.walk():
    added_data_values_setting.value[setting.get_path(added_actions_group)] = setting.value


def _set_values_for_actions(added_data_values_setting, added_actions_group):
  for setting in added_actions_group.walk():
    if setting.get_path(added_actions_group) in added_data_values_setting.value:
      setting.set_value(added_data_values_setting.value[setting.get_path(added_actions_group)])


def _create_action(
      name,
      function=None,
      arguments=None,
      enabled=True,
      display_name=None,
      description=None,
      action_groups=None,
      tags=None,
      more_options_expanded=False,
      enabled_for_previews=True,
      **custom_fields):
  
  def _set_display_name_for_enabled_gui(setting_enabled, setting_display_name):
    setting_display_name.set_gui(
      gui_type=pg.setting.SettingGuiTypes.check_button_label,
      gui_element=setting_enabled.gui.element)
  
  action = pg.setting.Group(
    name,
    tags=tags,
    setting_attributes={
      'pdb_type': None,
      'setting_sources': None,
    })
  
  arguments_group = pg.setting.Group(
    'arguments',
    setting_attributes={
      'pdb_type': None,
      'setting_sources': None,
    })
  
  if arguments:
    arguments_group.add(arguments)
  
  action.add([
    {
      'type': pg.SettingTypes.generic,
      'name': 'function',
      'default_value': function,
      'setting_sources': None,
    },
    arguments_group,
    {
      'type': pg.SettingTypes.boolean,
      'name': 'enabled',
      'default_value': enabled,
    },
    {
      'type': pg.SettingTypes.string,
      'name': 'display_name',
      'default_value': display_name,
      'gui_type': None,
      'tags': ['ignore_initialize_gui'],
    },
    {
      'type': pg.SettingTypes.string,
      'name': 'description',
      'default_value': description,
      'gui_type': None,
    },
    {
      'type': pg.SettingTypes.generic,
      'name': 'action_groups',
      'default_value': action_groups,
      'gui_type': None,
    },
    {
      "type": pg.SettingTypes.boolean,
      "name": 'more_options_expanded',
      "default_value": more_options_expanded,
      "display_name": _('_More options'),
      "gui_type": pg.SettingGuiTypes.expander,
    },
    {
      "type": pg.SettingTypes.boolean,
      "name": 'enabled_for_previews',
      "default_value": enabled_for_previews,
      "display_name": _('Enable for previews'),
    },
  ])
  
  orig_name_value = custom_fields.pop('orig_name', name)
  action.add([
    {
      'type': pg.SettingTypes.string,
      'name': 'orig_name',
      'default_value': orig_name_value,
      'gui_type': None,
    },
  ])
  
  for field_name, field_value in custom_fields.items():
    action.add([
      {
        'type': pg.SettingTypes.generic,
        'name': field_name,
        'default_value': field_value,
        'gui_type': None,
      },
    ])
  
  action['enabled'].connect_event(
    'after-set-gui',
    _set_display_name_for_enabled_gui,
    action['display_name'])
  
  if action.get_value('is_pdb_procedure', True):
    _connect_events_to_sync_array_and_array_length_arguments(action)
    _hide_gui_for_run_mode_and_array_length_arguments(action)
  
  return action


def _create_procedure(
      name,
      function,
      additional_tags=None,
      action_groups=(DEFAULT_PROCEDURES_GROUP,),
      **kwargs_and_custom_fields):
  tags = ['action', 'procedure']
  if additional_tags is not None:
    tags += additional_tags
  
  if action_groups is not None:
    action_groups = list(action_groups)
  
  return _create_action(
    name,
    function,
    action_groups=action_groups,
    tags=tags,
    **kwargs_and_custom_fields)


def _create_constraint(
      name,
      function,
      additional_tags=None,
      action_groups=(DEFAULT_CONSTRAINTS_GROUP,),
      subfilter=None,
      **kwargs_and_custom_fields):
  tags = ['action', 'constraint']
  if additional_tags is not None:
    tags += additional_tags
  
  if action_groups is not None:
    action_groups = list(action_groups)
  
  constraint = _create_action(
    name,
    function,
    action_groups=action_groups,
    tags=tags,
    **kwargs_and_custom_fields)
  
  constraint.add([
    {
      'type': pg.SettingTypes.string,
      'name': 'subfilter',
      'default_value': subfilter,
      'gui_type': None,
    },
  ])
  
  return constraint


def _connect_events_to_sync_array_and_array_length_arguments(action):
  
  def _increment_array_length(
        array_setting, insertion_index, value, array_length_setting):
    array_length_setting.set_value(array_length_setting.value + 1)
  
  def _decrement_array_length(
        array_setting, insertion_index, array_length_setting):
    array_length_setting.set_value(array_length_setting.value - 1)
  
  for length_setting, array_setting in _get_array_length_and_array_settings(action):
    array_setting.connect_event(
      'after-add-element', _increment_array_length, length_setting)
    array_setting.connect_event(
      'before-delete-element', _decrement_array_length, length_setting)


def _hide_gui_for_run_mode_and_array_length_arguments(action):
  first_argument = next(iter(action['arguments']), None)
  if first_argument is not None and first_argument.display_name == 'run-mode':
    first_argument.gui.set_visible(False)
  
  for length_setting, unused_ in _get_array_length_and_array_settings(action):
    length_setting.gui.set_visible(False)


def _get_array_length_and_array_settings(action):
  array_length_and_array_settings = []
  previous_setting = None
  
  for setting in action['arguments']:
    if isinstance(setting, pg.setting.ArraySetting) and previous_setting is not None:
      array_length_and_array_settings.append((previous_setting, setting))
    
    previous_setting = setting
  
  return array_length_and_array_settings


_ACTION_TYPES_AND_FUNCTIONS = {
  'procedure': _create_procedure,
  'constraint': _create_constraint
}


def add(actions, action_dict_or_function):
  """
  Add an action to the `actions` setting group.
  
  `action_dict_or_function` can be one of the following:
  * a dictionary - see `create()` for required and accepted fields.
  * a PDB procedure.
  
  Objects of other types passed to `action_dict_or_function` raise
  `TypeError`.
  
  The same action can be added multiple times. Each action will be
  assigned a unique name and display name (e.g. `'autocrop'` and `'Autocrop'`
  for the first action, `'autocrop_2'` and `'Autocrop (2)'` for the second
  action, and so on).
  """
  if isinstance(action_dict_or_function, dict):
    action_dict = dict(action_dict_or_function)
  else:
    if pg.pdbutils.is_pdb_procedure(action_dict_or_function):
      action_dict = get_action_dict_for_pdb_procedure(action_dict_or_function)
    else:
      raise TypeError(
        '"{}" is not a valid object - pass a dict or a PDB procedure'.format(
          action_dict_or_function))
  
  orig_action_dict = dict(action_dict)
  
  actions.invoke_event('before-add-action', action_dict)
  
  _uniquify_name_and_display_name(actions, action_dict)
  
  action = _create_action_by_type(**action_dict)
  
  actions['added'].add([action])
  actions['_added_data'].value.append(action_dict)
  
  actions.invoke_event('after-add-action', action, orig_action_dict)
  
  return action


def get_action_dict_for_pdb_procedure(pdb_procedure):
  """
  Return a dictionary representing the specified GIMP PDB procedure that can be
  added to a setting group for actions via `add()`.
  
  The `'function'` field contains the PDB procedure name instead of the function
  itself in order for the dictionary to allow loading/saving to a persistent
  source.
  
  If the procedure contains arguments with the same name, each subsequent
  identical name is made unique (since arguments are internally represented as
  `pygimplib.setting.Setting` instances, whose names must be unique within a
  setting group).
  """
  
  def _generate_unique_pdb_procedure_argument_name():
    i = 2
    while True:
      yield '-{}'.format(i)
      i += 1
  
  action_dict = {
    'name': pg.utils.safe_decode_gimp(pdb_procedure.proc_name),
    'function': pg.utils.safe_decode_gimp(pdb_procedure.proc_name),
    'arguments': [],
    'display_name': pg.utils.safe_decode_gimp(pdb_procedure.proc_name),
    'is_pdb_procedure': True,
  }
  
  pdb_procedure_argument_names = []
  
  for index, (pdb_param_type, pdb_param_name, unused_) in enumerate(pdb_procedure.params):
    processed_pdb_param_name = pg.utils.safe_decode_gimp(pdb_param_name)
    
    try:
      setting_type = pg.setting.PDB_TYPES_TO_SETTING_TYPES_MAP[pdb_param_type]
    except KeyError:
      raise UnsupportedPdbProcedureError(action_dict['name'], pdb_param_type)
    
    unique_pdb_param_name = pg.path.uniquify_string(
      processed_pdb_param_name,
      pdb_procedure_argument_names,
      uniquifier_generator=_generate_unique_pdb_procedure_argument_name())
    
    pdb_procedure_argument_names.append(unique_pdb_param_name)
    
    if isinstance(setting_type, dict):
      arguments_dict = dict(setting_type)
      arguments_dict['name'] = unique_pdb_param_name
      arguments_dict['display_name'] = processed_pdb_param_name
    else:
      arguments_dict = {
        'type': setting_type,
        'name': unique_pdb_param_name,
        'display_name': processed_pdb_param_name,
      }
    
    if pdb_param_type in placeholders.PDB_TYPES_TO_PLACEHOLDER_SETTING_TYPES_MAP:
      arguments_dict['type'] = (
        placeholders.PDB_TYPES_TO_PLACEHOLDER_SETTING_TYPES_MAP[pdb_param_type])
    
    if index == 0 and processed_pdb_param_name == 'run-mode':
      arguments_dict['default_value'] = gimpenums.RUN_NONINTERACTIVE
    
    action_dict['arguments'].append(arguments_dict)
  
  return action_dict


def _uniquify_name_and_display_name(actions, action_dict):
  action_dict['orig_name'] = action_dict['name']
  
  action_dict['name'] = _uniquify_action_name(
    actions, action_dict['name'])
  
  action_dict['display_name'] = _uniquify_action_display_name(
    actions, action_dict['display_name'])


def _uniquify_action_name(actions, name):
  """
  Return `name` modified to not match the name of any existing action in
  `actions`.
  """
  
  def _generate_unique_action_name():
    i = 2
    while True:
      yield '_{}'.format(i)
      i += 1
  
  return (
    pg.path.uniquify_string(
      name,
      [action.name for action in walk(actions)],
      uniquifier_generator=_generate_unique_action_name()))


def _uniquify_action_display_name(actions, display_name):
  """
  Return `display_name` modified to not match the display name of any existing
  action in `actions`.
  """
  
  def _generate_unique_display_name():
    i = 2
    while True:
      yield ' ({})'.format(i)
      i += 1
  
  return (
    pg.path.uniquify_string(
      display_name,
      [action['display_name'].value for action in walk(actions)],
      uniquifier_generator=_generate_unique_display_name()))


def reorder(actions, action_name, new_position):
  """
  Modify the position of the added action given by its name to the new
  position specified as an integer.
  
  A negative position functions as an n-th to last position (-1 for last, -2
  for second to last, etc.).
  
  Raises:
  * `ValueError` - `action_name` not found in `actions`.
  """
  current_position = _find_index_in_added_data(actions, action_name)
  
  if current_position is None:
    raise ValueError('action "{}" not found in actions named "{}"'.format(
      action_name, actions.name))
  
  action = actions['added'][action_name]
  
  actions.invoke_event('before-reorder-action', action, current_position)
  
  action_dict = actions['_added_data'].value.pop(current_position)
  
  if new_position < 0:
    new_position = max(len(actions['_added_data'].value) + new_position + 1, 0)
  
  actions['_added_data'].value.insert(new_position, action_dict)
  
  actions.invoke_event(
    'after-reorder-action', action, current_position, new_position)


def remove(actions, action_name):
  """
  Remove the action specified by its name from `actions`.
  
  Raises:
  * `ValueError` - `action_name` not found in `actions`.
  """
  action_index = _find_index_in_added_data(actions, action_name)
  
  if action_index is None:
    raise ValueError('action "{}" not found in actions named "{}"'.format(
      action_name, actions.name))
  
  action = actions['added'][action_name]
  
  actions.invoke_event('before-remove-action', action)
  
  actions['added'].remove([action_name])
  del actions['_added_data'].value[action_index]
  
  actions.invoke_event('after-remove-action', action_name)


def _find_index_in_added_data(actions, action_name):
  return next(
    (index for index, dict_ in enumerate(actions['_added_data'].value)
     if dict_['name'] == action_name),
    None)


def clear(actions):
  """
  Remove all added actions.
  """
  actions.invoke_event('before-clear-actions')
  
  _clear(actions)
  
  actions.invoke_event('after-clear-actions')


def _clear(actions):
  actions['added'].remove([action.name for action in walk(actions)])
  actions['_added_data'].reset()
  actions['_added_data_values'].reset()


def walk(actions, action_type=None, setting_name=None):
  """
  Walk (iterate over) a setting group containing actions.
  
  The value of `action_type` determines what types of actions to iterate
  over. If `action_type` is `None`, iterate over all actions. For allowed
  action types, see `create()`. Invalid values for `action_type` raise
  `ValueError`.
  
  If `setting_name` is `None`, iterate over each setting group representing the
  entire action.
  
  If `setting_name` is not `None`, iterate over each setting or subgroup inside
  each action. For example, `'enabled'` yields the `'enabled'` setting for
  each action. For the list of possible names of settings and subgroups, see
  `create()`.
  """
  action_types = list(_ACTION_TYPES_AND_FUNCTIONS)
  
  if action_type is not None and action_type not in action_types:
    raise ValueError('invalid action type "{}"'.format(action_type))
  
  def has_matching_type(setting):
    if action_type is None:
      return any(type_ in setting.tags for type_ in action_types)
    else:
      return action_type in setting.tags
  
  listed_actions = {
    setting.name: setting
    for setting in actions['added'].walk(
      include_setting_func=has_matching_type,
      include_groups=True,
      include_if_parent_skipped=True)}
  
  for action_dict in actions['_added_data'].value:
    if action_dict['name'] in listed_actions:
      action = listed_actions[action_dict['name']]
      
      if setting_name is None:
        yield action
      else:
        if setting_name in action:
          yield action[setting_name]


class UnsupportedPdbProcedureError(Exception):
  
  def __init__(self, procedure_name, unsupported_param_type):
    self.procedure_name = procedure_name
    self.unsupported_param_type = unsupported_param_type
