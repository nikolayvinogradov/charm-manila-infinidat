#! /usr/bin/env python3

# Copyright 2021 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import OrderedDict
import ops_openstack.adapters
from ops_openstack.plugins.classes import CinderStoragePluginCharm
from ops_openstack.core import charm_class, get_charm_class_for_release, OSBaseCharm
from ops.main import main

from ops.model import (
    ActiveStatus,
    BlockedStatus,
)

from charmhelpers.core.host import (
    lsb_release,
)

from charmhelpers.fetch import (
    apt_install,
    apt_update,
    add_source,
)

import charmhelpers.contrib.openstack.templating as os_templating

from charmhelpers.core.templating import render

import json

import logging

RELATION_NAME = 'manila-plugin'

class ManilaInfinidatPluginCharm(OSBaseCharm):

    PACKAGES = ['infinisdk', 'infinishell']

    REQUIRED_RELATIONS = [RELATION_NAME]

    SHARE_DRIVER = 'manila.share.drivers.infinidat.infinibox.InfiniboxShareDriver'

    active_active = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
            
        self.framework.observe(
            self.on.config_changed,
            self.on_config)

        self.framework.observe(
            self.on.manila_plugin_relation_changed,
            self.on_manila_plugin)

    def on_config(self, event):
        self.on_manila_plugin(event)
        self.set_started(started=True)
        self.unit.status = ActiveStatus('Unit is ready')

    def on_manila_plugin(self, event):
        logging.error("Relation changed")
        config = dict(self.framework.model.config)
        manila_backends = self.manila_configuration(config)
        for relation in self.framework.model.relations.get(RELATION_NAME):
            relation.data[self.unit]['_name'] = ','.join(manila_backends.keys())
            rendered_config = render(
                source="parts/backends",
                template_loader=os_templating.get_loader(
                    'templates/', "focal"),
                target=None,
                context={'backends': manila_backends})

            relation.data[self.unit]['_configuration_data'] = json.dumps({
                'data': {
                    '/etc/manila/manila.conf': rendered_config
                }
            })

    def manila_configuration(self, config):
        """
        See https://docs.openstack.org/manila/latest/configuration/shared-file-systems/drivers/infinidat-share-driver.html # noqa: E501
        """
        # Return the configuration to be set by the principal.
        
        backends = OrderedDict()

        backend_name = config.get('share-backend-name')

        # backend name selection logic
        if config.get('nas-network-space-name'):
            backend_names = filter(
                map(
                    str.strip,
                    config.get('nas-network-space-name').split(',')
                )
            )
        elif backend_name == '__app__':
            backend_names = [self.framework.model.app.name]
        elif backend_name:
            backend_names = [backend_name]

        for backend_name in backend_names:

            backends[backend_name] = (
                ('share_driver', self.SHARE_DRIVER),
                ('share_backend_name', backend_name),
                
                ('infinibox_hostname', config.get('infinibox-ip')),
                ('infinibox_login', config.get('infinibox-login')),
                ('infinibox_password', config.get('infinibox-password')),

                ('infinidat_nas_network_space_name', backend_name), #TODO: mapping to nas-network-space-name

                ('infinidat_pool_name', config.get('pool-name')),
                ('infinidat_thin_provision', config.get('thin-provision')),
            )

        if not backends:
            self.unit.status = BlockedStatus("No backends configured")

        return backends

    @property
    def stateless(self):
        """Indicate whether the charm is stateless.

        For more information, see: https://cinderlib.readthedocs.io/en/v0.2.1/topics/serialization.html

        :returns: A boolean value indicating statefulness.
        :rtype: bool
        """   # noqa
        return False

    @property
    def active_active(self):
        """Indicate active-active support in the charm.

        For more information, see: https://specs.openstack.org/openstack/cinder-specs/specs/mitaka/cinder-volume-active-active-support.html

        :returns: A boolean indicating active-active support.
        :rtype: bool
        """   # noqa
        return False

    def install_pkgs(self):
        logging.info("Installing packages")

        # value of 'source' param is defined like this:
        # deb https://repo.infinidat.com/packages/main-stable/apt/linux-ubuntu $codename main
        if self.model.config.get('source'):
            add_source(
                self.model.config['source'] \
                    .replace('$codename',
                        lsb_release()['DISTRIB_CODENAME'].lower()),
                self.model.config.get('key'))
        apt_update(fatal=True)
        apt_install(self.PACKAGES, fatal=True)
        self.update_status()

    def on_install(self, event):
        self.install_pkgs()

        self.update_status()

if __name__ == '__main__':
    main(ManilaInfinidatPluginCharm)
