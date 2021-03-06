#!/usr/bin/python
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'network'}


DOCUMENTATION = '''
---
module: nxos_interface_ospf
extends_documentation_fragment: nxos
version_added: "2.2"
short_description: Manages configuration of an OSPF interface instance.
description:
  - Manages configuration of an OSPF interface instance.
author: Gabriele Gerbino (@GGabriele)
notes:
  - Default, where supported, restores params default value.
  - To remove an existing authentication configuration you should use
    C(message_digest_key_id=default) plus all other options matching their
    existing values.
  - C(state=absent) removes the whole OSPF interface configuration.
options:
  interface:
    description:
        - Name of this cisco_interface resource. Valid value is a string.
    required: true
  ospf:
    description:
      - Name of the ospf instance.
    required: true
  area:
    description:
      - Ospf area associated with this cisco_interface_ospf instance.
        Valid values are a string, formatted as an IP address
        (i.e. "0.0.0.0") or as an integer.
    required: true
  cost:
    description:
      - The cost associated with this cisco_interface_ospf instance.
    required: false
    default: null
  hello_interval:
    description:
      - Time between sending successive hello packets.
        Valid values are an integer or the keyword 'default'.
    required: false
    default: null
  dead_interval:
    description:
      - Time interval an ospf neighbor waits for a hello
        packet before tearing down adjacencies. Valid values are an
        integer or the keyword 'default'.
    required: false
    default: null
  passive_interface:
    description:
      - Setting to true will prevent this interface from receiving
        HELLO packets. Valid values are 'true' and 'false'.
    required: false
    choices: ['true','false']
    default: null
  message_digest:
    description:
      - Enables or disables the usage of message digest authentication.
        Valid values are 'true' and 'false'.
    required: false
    choices: ['true','false']
    default: null
  message_digest_key_id:
    description:
      - Md5 authentication key-id associated with the ospf instance.
        If this is present, message_digest_encryption_type,
        message_digest_algorithm_type and message_digest_password are
        mandatory. Valid value is an integer and 'default'.
    required: false
    default: null
  message_digest_algorithm_type:
    description:
      - Algorithm used for authentication among neighboring routers
        within an area. Valid values is 'md5'.
    required: false
    choices: ['md5']
    default: null
  message_digest_encryption_type:
    description:
      - Specifies the scheme used for encrypting message_digest_password.
        Valid values are '3des' or 'cisco_type_7' encryption.
    required: false
    choices: ['cisco_type_7','3des']
    default: null
  message_digest_password:
    description:
      - Specifies the message_digest password. Valid value is a string.
    required: false
    default: null
  state:
    description:
      - Determines whether the config should be present or not
        on the device.
    required: false
    default: present
    choices: ['present','absent']
'''
EXAMPLES = '''
- nxos_interface_ospf:
    interface: ethernet1/32
    ospf: 1
    area: 1
    cost: default
'''

RETURN = '''
commands:
    description: commands sent to the device
    returned: always
    type: list
    sample: ["interface Ethernet1/32", "ip router ospf 1 area 0.0.0.1"]
'''


import re
from ansible.module_utils.nxos import get_config, load_config
from ansible.module_utils.nxos import nxos_argument_spec, check_args
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.netcfg import CustomNetworkConfig

BOOL_PARAMS = [
    'passive_interface',
    'message_digest'
]
PARAM_TO_COMMAND_KEYMAP = {
    'interface': '',
    'cost': 'ip ospf cost',
    'ospf': 'ip router ospf',
    'area': 'ip router ospf',
    'hello_interval': 'ip ospf hello-interval',
    'dead_interval': 'ip ospf dead-interval',
    'passive_interface': 'ip ospf passive-interface',
    'message_digest': 'ip ospf authentication message-digest',
    'message_digest_key_id': 'ip ospf message-digest-key',
    'message_digest_algorithm_type': 'ip ospf message-digest-key',
    'message_digest_encryption_type': 'ip ospf message-digest-key',
    'message_digest_password': 'ip ospf message-digest-key',
}


def get_value(arg, config, module):
    command = PARAM_TO_COMMAND_KEYMAP[arg]
    has_command = re.search(r'\s+{0}\s*$'.format(command), config, re.M)
    has_command_val = re.search(r'(?:{0}\s)(?P<value>.*)$'.format(command), config, re.M)

    if command == 'ip router ospf':
        value = ''
        if has_command_val:
            value_list = has_command_val.group('value').split()
            if arg == 'ospf':
                value = value_list[0]
            elif arg == 'area':
                value = value_list[2]
    elif command == 'ip ospf message-digest-key':
        value = ''
        if has_command_val:
            value_list = has_command_val.group('value').split()
            if arg == 'message_digest_key_id':
                value = value_list[0]
            elif arg == 'message_digest_algorithm_type':
                value = value_list[1]
            elif arg == 'message_digest_encryption_type':
                value = value_list[2]
                if value == '3':
                    value = '3des'
                elif value == '7':
                    value = 'cisco_type_7'
            elif arg == 'message_digest_password':
                value = value_list[3]
    elif arg == 'passive_interface':
        has_no_command = re.search(r'\s+no\s+{0}\s*$'.format(command), config, re.M)
        value = False
        if has_command and not has_no_command:
            value = True
    elif arg in BOOL_PARAMS:
        value = bool(has_command)
    else:
        value = ''
        if has_command_val:
            value = has_command_val.group('value')
    return value


def get_existing(module, args):
    existing = {}
    netcfg = CustomNetworkConfig(indent=2, contents=get_config(module))
    if module.params['interface'].startswith('loopback') or module.params['interface'].startswith('port-channel'):
        parents = ['interface {0}'.format(module.params['interface'])]
    else:
        parents = ['interface {0}'.format(module.params['interface'].capitalize())]
    config = netcfg.get_section(parents)
    if 'ospf' in config:
        for arg in args:
            if arg not in ['interface']:
                existing[arg] = get_value(arg, config, module)
        existing['interface'] = module.params['interface']
    return existing


def apply_key_map(key_map, table):
    new_dict = {}
    for key, value in table.items():
        new_key = key_map.get(key)
        if new_key:
            new_dict[new_key] = value
    return new_dict


def get_default_commands(existing, proposed, existing_commands, key, module):
    commands = list()
    existing_value = existing_commands.get(key)
    if key.startswith('ip ospf message-digest-key'):
        check = False
        for param in ['message_digest_encryption_type',
                      'message_digest_algorithm_type',
                      'message_digest_password']:
            if existing[param] == proposed[param]:
                check = True
        if check:
            if existing['message_digest_encryption_type'] == '3des':
                encryption_type = '3'
            elif existing['message_digest_encryption_type'] == 'cisco_type_7':
                encryption_type = '7'
            command = 'no {0} {1} {2} {3} {4}'.format(
                key,
                existing['message_digest_key_id'],
                existing['message_digest_algorithm_type'],
                encryption_type,
                existing['message_digest_password'])
            commands.append(command)
    else:
        commands.append('no {0} {1}'.format(key, existing_value))
    return commands


def get_custom_command(existing_cmd, proposed, key, module):
    commands = list()

    if key == 'ip router ospf':
        command = '{0} {1} area {2}'.format(key, proposed['ospf'],
                                            proposed['area'])
        if command not in existing_cmd:
            commands.append(command)

    elif key.startswith('ip ospf message-digest-key'):
        if (proposed['message_digest_key_id'] != 'default' and
                'options' not in key):
            if proposed['message_digest_encryption_type'] == '3des':
                encryption_type = '3'
            elif proposed['message_digest_encryption_type'] == 'cisco_type_7':
                encryption_type = '7'
            command = '{0} {1} {2} {3} {4}'.format(
                key,
                proposed['message_digest_key_id'],
                proposed['message_digest_algorithm_type'],
                encryption_type,
                proposed['message_digest_password'])
            commands.append(command)
    return commands


def state_present(module, existing, proposed, candidate):
    commands = list()
    proposed_commands = apply_key_map(PARAM_TO_COMMAND_KEYMAP, proposed)
    existing_commands = apply_key_map(PARAM_TO_COMMAND_KEYMAP, existing)

    for key, value in proposed_commands.items():
        if existing_commands.get(key):
            if key == 'ip router ospf':
                if proposed['area'] == existing['area']:
                    continue
            if existing_commands[key] == proposed_commands[key]:
                continue

        if value is True:
            commands.append(key)
        elif value is False:
            commands.append('no {0}'.format(key))
        elif value == 'default':
            if existing_commands.get(key):
                commands.extend(get_default_commands(existing, proposed,
                                                     existing_commands, key,
                                                     module))
        else:
            if (key == 'ip router ospf' or
                    key.startswith('ip ospf message-digest-key')):
                commands.extend(get_custom_command(commands, proposed,
                                                   key, module))
            else:
                command = '{0} {1}'.format(key, value.lower())
                commands.append(command)

    if commands:
        parents = ['interface {0}'.format(module.params['interface'].capitalize())]
        candidate.add(commands, parents=parents)


def state_absent(module, existing, proposed, candidate):
    commands = []
    parents = ['interface {0}'.format(module.params['interface'].capitalize())]
    existing_commands = apply_key_map(PARAM_TO_COMMAND_KEYMAP, existing)

    for key, value in existing_commands.items():
        if value:
            if key.startswith('ip ospf message-digest-key'):
                if 'options' not in key:
                    if existing['message_digest_encryption_type'] == '3des':
                        encryption_type = '3'
                    elif existing['message_digest_encryption_type'] == 'cisco_type_7':
                        encryption_type = '7'
                    command = 'no {0} {1} {2} {3} {4}'.format(
                        key,
                        existing['message_digest_key_id'],
                        existing['message_digest_algorithm_type'],
                        encryption_type,
                        existing['message_digest_password'])
                    commands.append(command)
            elif key in ['ip ospf authentication message-digest',
                         'ip ospf passive-interface']:
                if value:
                    commands.append('no {0}'.format(key))
            elif key == 'ip router ospf':
                command = 'no {0} {1} area {2}'.format(key, proposed['ospf'], proposed['area'])
                if command not in commands:
                    commands.append(command)
            else:
                existing_value = existing_commands.get(key)
                commands.append('no {0} {1}'.format(key, existing_value))

    candidate.add(commands, parents=parents)


def normalize_area(area, module):
    try:
        area = int(area)
        area = '0.0.0.{0}'.format(area)
    except ValueError:
        splitted_area = area.split('.')
        if len(splitted_area) != 4:
            module.fail_json(msg='Incorrect Area ID format', area=area)
    return area


def main():
    argument_spec = dict(
        interface=dict(required=True, type='str'),
        ospf=dict(required=True, type='str'),
        area=dict(required=True, type='str'),
        cost=dict(required=False, type='str'),
        hello_interval=dict(required=False, type='str'),
        dead_interval=dict(required=False, type='str'),
        passive_interface=dict(required=False, type='bool'),
        message_digest=dict(required=False, type='bool'),
        message_digest_key_id=dict(required=False, type='str'),
        message_digest_algorithm_type=dict(required=False, type='str', choices=['md5']),
        message_digest_encryption_type=dict(required=False, type='str', choices=['cisco_type_7', '3des']),
        message_digest_password=dict(required=False, type='str', no_log=True),
        state=dict(choices=['present', 'absent'], default='present', required=False),
        include_defaults=dict(default=True),
        config=dict(),
        save=dict(type='bool', default=False)
    )

    argument_spec.update(nxos_argument_spec)

    module = AnsibleModule(argument_spec=argument_spec,
                           required_together=[['message_digest_key_id',
                                               'message_digest_algorithm_type',
                                               'message_digest_encryption_type',
                                               'message_digest_password']],
                           supports_check_mode=True)

    if not module.params['interface'].startswith('loopback') and not module.params['interface'].startswith('port-channel'):
        module.params['interface'] = module.params['interface'].capitalize()

    warnings = list()
    check_args(module, warnings)
    result = {'changed': False, 'commands': [], 'warnings': warnings}

    for param in ['message_digest_encryption_type',
                  'message_digest_algorithm_type',
                  'message_digest_password']:
        if module.params[param] == 'default':
            module.exit_json(msg='Use message_digest_key_id=default to remove an existing authentication configuration')

    state = module.params['state']
    args = PARAM_TO_COMMAND_KEYMAP.keys()

    existing = get_existing(module, args)
    proposed_args = dict((k, v) for k, v in module.params.items()
                         if v is not None and k in args)

    proposed = {}
    for key, value in proposed_args.items():
        if key != 'interface':
            if str(value).lower() == 'true':
                value = True
            elif str(value).lower() == 'false':
                value = False
            elif str(value).lower() == 'default':
                value = 'default'
            if existing.get(key) or (not existing.get(key) and value):
                proposed[key] = value

    proposed['area'] = normalize_area(proposed['area'], module)

    candidate = CustomNetworkConfig(indent=3)
    if state == 'present':
        state_present(module, existing, proposed, candidate)
    elif state == 'absent' and existing.get('ospf') == proposed['ospf'] and existing.get('area') == proposed['area']:
        state_absent(module, existing, proposed, candidate)

    if candidate:
        candidate = candidate.items_text()
        load_config(module, candidate)
        result['changed'] = True
        result['commands'] = candidate

    module.exit_json(**result)


if __name__ == '__main__':
    main()
