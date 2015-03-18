#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
# Author: Davide Guerri <davide.guerri@hp.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

try:
    import shade

    HAS_SHADE = True
except ImportError:
    HAS_SHADE = False

DOCUMENTATION = '''
---
module: os_keystone_service
version_added: "1.9"
short_description: Manage OpenStack Identity (keystone) endpoints
extends_documentation_fragment: openstack
description:
   - Manage endpoints from OpenStack.
options:
   name:
     description:
        - OpenStack service name (e.g. keystone)
     required: true
   service_type:
     description:
        - OpenStack service type (e.g. identity)
     required: true
   description:
     description:
        - Service description
     required: false
     default: Not provided
   state:
     description:
        - Indicate desired state of the resource
     choices: ['present', 'absent']
     default: present
requirements: ["shade"]
author: Davide Guerri
'''

EXAMPLES = '''
# Add Glance service
- os_keystone_service: >
    name=glance
    service_type=image
    description="Glance image service"

# Delete Glance service
- os_keystone_service: >
    name=glance
    service_type=image
    description="Glance image service"
    state=absent
'''


def service_exists(cloud, service_name):
    """ Return True if service already exists"""
    return service_name in [x.name for x in cloud.services.list()]


def get_service(cloud, service_name):
    """ Retrieve a service by name"""
    services = [x for x in cloud.services.list() if x.name == service_name]
    count = len(services)
    if count == 0:
        raise KeyError("No service with name %s" % service_name)
    elif count > 1:
        # Should never be reached as Keystone ensure service names to be unique
        raise ValueError("%d services with name %s" % (count, service_name))
    else:
        return services[0]


def get_service_id(cloud, service_name):
    return get_service(cloud, service_name).id


def ensure_service_exists(cloud, service_name, service_type,
                          service_description, check_mode):
    """ Ensure that a service exists.

        Return (True, id) if a new service was created, (False, None) if it
        already existed.
    """

    # Check if service already exists
    try:
        service = get_service(cloud=cloud, service_name=service_name)
    except KeyError:
        # Service doesn't exist yet
        pass
    else:
        return False, service.id

    # We now know we will have to create a new service
    if check_mode:
        return True, None

    ks_service = cloud.services.create(name=service_name,
                                       service_type=service_type,
                                       description=service_description)
    return True, ks_service.id


def ensure_service_absent(cloud, service_name, check_mode):
    """ Ensure that a service does not exist

         Return True if the service was removed, False if it didn't exist
         in the first place
    """
    if not service_exists(cloud=cloud, service_name=service_name):
        return False

    # We now know we will have to delete the service
    if check_mode:
        return True

    service = get_service(cloud=cloud, service_name=service_name)
    cloud.services.delete(service.id)


def main():
    argument_spec = openstack_full_argument_spec(
        name=dict(required=True),
        service_type=dict(required=True),
        description=dict(required=False, default="Not provided"),
        state=dict(default='present', choices=['present', 'absent']),
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    if not HAS_SHADE:
        module.fail_json(msg='shade is required for this module')

    service_name = module.params['name']
    service_type = module.params['service_type']
    service_description = module.params['description']
    state = module.params['state']

    check_mode = module.check_mode

    _id = None
    try:
        cloud = shade.openstack_cloud(**module.params)

        if state == "present":
            changed, _id = ensure_service_exists(
                cloud=cloud,
                service_name=service_name,
                service_type=service_type,
                service_description=service_description,
                check_mode=check_mode)
        elif state == "absent":
            changed = ensure_service_absent(
                cloud=cloud,
                service_name=service_name,
                check_mode=check_mode)
        else:
            # Invalid state
            raise ValueError("Invalid state %s" % state)
    except Exception, e:
        if check_mode:
            # If we have a failure in check mode
            module.exit_json(changed=True,
                             msg="exception: %s" % e)
        else:
            module.fail_json(msg="exception: %s" % e)
    else:
        module.exit_json(changed=changed, id=_id)


# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *

if __name__ == '__main__':
    main()
