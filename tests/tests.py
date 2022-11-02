#!/usr/bin/env python3

# Copyright 2022 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Encapsulate manila-infinidat testing."""


import zaza.openstack.charm_tests.test_utils as test_utils
import zaza.openstack.charm_tests.manila.tests as manila_tests
from manilaclient import client as manilaclient

def configure_infinidat_share_type():
    mcl = manilaclient.Client(
                       session=cls.keystone_session,
                       client_version='2',
                       cacert='/var/snap/openstackclients/common/cacert')

    share_type = mcl.share_types.find(name='infinidat')
    if not share_type:
        share_type = mcl.share_types.create(name='infinidat',
                specs_driver_handles_file_share=False)

class ManilaInfinidatTest(manila_tests.ManilaBaseTest):
    """Encapsulate Manila Infinidat NFS test."""

    @classmethod
    def setUpClass(cls):
        """Run class setup for running tests."""
        super(manila_tests.ManilaBaseTest, cls).setUpClass()

        auth = openstack_utils.get_overcloud_auth()

        # for some reason manilaclient ignores OS_CACERT when
        # it comes to requesting shares API, and it seems to
        # be ignoring keystoneclient's 'session' as well.
        # https://bugs.launchpad.net/python-manilaclient/+bug/1989577
        # might be relevant
        mcl = manilaclient.Client(
                            session=cls.keystone_session,
                            client_version='2',
                            cacert=auth.get('OS_CACERT',None))

        mcl = openstack_utils.get_manila_session_client(cls.keystone_session)

        cls.nova_client = openstack_utils.get_nova_session_client(
            session=cls.keystone_session)
        cls.manila_client = mcl
        cls.mount_dir = '/mnt/manila_share'
        cls.share_name = 'infinidat-share'
        cls.share_type_name = 'infinidat'
        cls.share_protocol = 'nfs'
        cls.share_network = None
