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
module: os_keystone_endpoint
version_added: "1.9"
short_description: Manage OpenStack Identity (keystone) endpoints
extends_documentation_fragment: openstack
description:
   - Manage endpoints from OpenStack.
options:
   service_name:
     description:
        - OpenStack service name (e.g. keystone)
     required: true
   region:
     description:
        - OpenStack region to which endpoint will be added
     required: false
     default: None
   public_url:
     description:
        - Public endpoint URL
     required: true
   internal_url:
     description:
        - Internal endpoint URL
     required: false
     default: None
   admin_url:
     description:
        - Admin endpoint URL
     required: false
     default: None
   state:
     description:
        - Indicate desired state of the resource
     choices: ['present', 'absent']
     default: present
requirements: ["shade"]
author: Davide Guerri
'''

EXAMPLES = '''
# Create a Glance endpoint in region aw1
- name: Create Glance endpoints
  os_keystone_endpoint: >
    service_name="glance"
    region="aw1"
    public_url="https://glance.aw1.bigcompany.com/"
    internal_url="http://glance-aw1.internal:9292/"
    admin_url="https://glance.aw1.bigcompany.com/"
    state=present

# Delete a Keystone endpoint in region aw2
- name: Delete Glance endpoints
  os_keystone_endpoint: >
    service_name="glance"
    region="aw2"
    public_url="https://glance.aw1.bigcompany.com/"
    internal_url="http://glance-aw1.internal:9292/"
    admin_url="https://glance.aw1.bigcompany.com/"
    state="absent"
'''


def endpoint_match(endpoint, service_id, region, public_url, internal_url,
                   admin_url):
    return endpoint.service_id == service_id and \
           endpoint.region == region and \
           endpoint.publicurl == public_url and \
           getattr(endpoint, 'internalurl') == internal_url and \
           getattr(endpoint, 'adminurl') == admin_url


def get_service(cloud, service_name):
    """ Retrieve a service by name"""
    services = [x for x in cloud.services.list() if x.name == service_name]
    count = len(services)
    if count == 0:
        raise KeyError("No keystone services with name %s" % service_name)
    elif count > 1:
        raise ValueError("%d services with name %s" % (count, service_name))
    else:
        return services[0]


def endpoint_exists(cloud, service_id, region, public_url, internal_url,
                    admin_url):
    """ Return True if endpoint already exists"""
    endpoints = [x for x in cloud.endpoints.list() if
                 endpoint_match(x, service_id, region, public_url, internal_url,
                                admin_url)]

    return any(endpoints)


def get_endpoint(cloud, service_id, region, public_url, internal_url,
                 admin_url):
    """ Retrieve an endpoint by name"""
    endpoints = [x for x in cloud.endpoints.list() if
                 endpoint_match(x, service_id, region, public_url, internal_url,
                                admin_url)]
    count = len(endpoints)
    if count == 0:
        raise KeyError(
            "No keystone endpoint with service id: %s, region: %s, public_url: "
            "%s, internal_url: %s, admin_url: %s" % (
                service_id, region, public_url, internal_url, admin_url))
    elif count > 1:
        # Should never be reached as Keystone ensure endpoints to be unique
        raise ValueError(
            "%d services with service id: %s, region: %s, public_url: %s, "
            "internal_url: %s, admin_url: %s" % (
                count, service_id, region, public_url, internal_url, admin_url))
    else:
        return endpoints[0]


def ensure_endpoint_exists(cloud, service_name, region, public_url,
                           internal_url, admin_url, check_mode):
    """ Ensure that an endpoint exists.

        Return (True, id) if a new endpoint was created, (False, None) if it
        already existed.
    """

    # Check if endpoint already exists
    service_id = get_service(cloud, service_name).id
    try:
        endpoint = get_endpoint(cloud=cloud, service_id=service_id,
                                region=region, public_url=public_url,
                                internal_url=internal_url, admin_url=admin_url)
    except KeyError:
        # endpoint doesn't exist yet
        pass
    else:
        return False, endpoint.id

    # We now know we will have to create a new service
    if check_mode:
        return True, None

    ks_service = cloud.endpoints.create(service_id=service_id,
                                        region=region,
                                        publicurl=public_url,
                                        internalurl=internal_url,
                                        adminurl=admin_url)
    return True, ks_service.id


def ensure_endpoint_absent(cloud, service_name, region, public_url,
                           internal_url, admin_url, check_mode):
    """ Ensure that an endpoint does not exist

         Return True if the endpoint was removed, False if it didn't exist
         in the first place
    """
    service_id = get_service(cloud, service_name).id
    if not endpoint_exists(cloud=cloud, service_id=service_id,
                           region=region, public_url=public_url,
                           internal_url=internal_url, admin_url=admin_url):
        return False

    # We now know we will have to delete the tenant
    if check_mode:
        return True

    endpoint = get_endpoint(cloud=cloud, service_id=service_id,
                            region=region, public_url=public_url,
                            internal_url=internal_url, admin_url=admin_url)
    cloud.endpoints.delete(endpoint.id)


def main():
    argument_spec = openstack_full_argument_spec(
        service_name=dict(required=True),
        region=dict(false=True, default=None),
        public_url=dict(required=True),
        internal_url=dict(required=False, default=None),
        admin_url=dict(required=False, default=None),
        state=dict(default='present', choices=['present', 'absent']),
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    if not HAS_SHADE:
        module.fail_json(msg='shade is required for this module')

    service_name = module.params['service_name']
    region = module.params['region']
    public_url = module.params['public_url']
    internal_url = module.params['internal_url']
    admin_url = module.params['admin_url']
    state = module.params['state']

    check_mode = module.check_mode

    _id = None
    try:
        cloud = shade.openstack_cloud(**module.params)

        if state == "present":
            changed, _id = ensure_endpoint_exists(
                cloud=cloud,
                service_name=service_name,
                region=region,
                public_url=public_url,
                internal_url=internal_url,
                admin_url=admin_url,
                check_mode=check_mode)
        elif state == "absent":
            changed = ensure_endpoint_absent(
                cloud=cloud,
                service_name=service_name,
                region=region,
                public_url=public_url,
                internal_url=internal_url,
                admin_url=admin_url,
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
