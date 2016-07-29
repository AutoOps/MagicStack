# -*- coding: utf-8 -*-
from tempfile import NamedTemporaryFile
import os.path
import json

from passlib.hash import sha512_crypt
from django.template.loader import get_template
from django.template import Context
from common.interface import APIRequest
from MagicStack.api import logger, CRYPTOR


API_DIR = os.path.dirname(os.path.abspath(__file__))
ANSIBLE_DIR = os.path.join(API_DIR, 'playbooks')


class MyTask(object):
    """
    this is a tasks object for include the common command.
    """
    def __init__(self, resource, host_list):
        self.resource = resource
        self.host_list = host_list
        self.run_action = 'sync'               # 执行动作为同步还是异步 sync:同步  async:异步
        self.run_type = 'ad-hoc'               # 执行ansible ad-hoc命令还是执行ansible playbook
        self.isTemplate = False                # 是否需要渲染模板

    def push_key(self, user, key_path, proxy, web_username):
        """
        push the ssh authorized key to target.
        """
        self.run_action = 'async'
        self.run_type = 'ad-hoc'
        module_args = 'user="%s" key="{{ lookup("file", "%s") }}" state=present' % (user, key_path)
        data = {'mod_name': 'authorized_key',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args,
                'role_name': user,
                'web_username': web_username,
                'run_action': self.run_action,
                'run_type': self.run_type,
                'isTemplate': self.isTemplate
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result

    def del_key(self, user, key_path, proxy):
        """
        push the ssh authorized key to target.
        """

        module_args = 'user="%s" key="{{ lookup("file", "%s") }}" state="absent"' % (user, key_path)
        data = {'mod_name': 'authorized_key',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args,
                'role_name': user
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR(proxy.password))
        result, code = api.req_post(data)
        return result

    def add_user(self, username, proxy, groups, web_username):
        """
        add a host user.
        username: 系统用户名
        web_username: 网站用户名
        """
        self.run_action = 'async'
        self.run_type = 'ad-hoc'
        if groups.strip():
            module_args = 'name=%s shell=/bin/bash groups=%s' % (username, groups)
        else:
            module_args = 'name=%s shell=/bin/bash' % username

        data = {'mod_name': 'user',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args,
                'role_name': username,
                'web_username': web_username,
                'run_action': self.run_action,
                'run_type': self.run_type,                    # 标记, 执行ansible ad-hoc命令还是执行playbook
                'isTemplate': self.isTemplate
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result

    def del_user(self, username, proxy, web_username):
        """
        delete a host user.
        """
        module_args = 'name=%s groups='' state=absent remove=yes move_home=yes force=yes' % username
        data = {'mod_name': 'user',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args,
                'role_name': username,
                'web_username': web_username,
                'run_action': 'sync',                       # run_action参数表示同步还是异步执行
                'run_type': 'ad-hoc'
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result

    def del_user_sudo(self, role_uuid, proxy, web_username):
        """
        delete a role sudo item
        """
        filename = 'role-%s'%role_uuid
        module_args = "name=/etc/sudoers.d/%s  state=absent" %filename
        data = {'mod_name': 'file',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args,
                'web_username': web_username,
                'run_action': 'sync',
                'run_type': 'ad-hoc'
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result

    def push_sudo(self, role, sudo_uuids, proxy, web_username):
        """
        use template to render pushed sudoers file
        """
        self.run_action = 'async'
        self.run_type = 'playbook'
        data = {'resource': self.resource,
                'hosts': self.host_list,
                'sudo_uuids': sudo_uuids,
                'role_name': role.name,
                'role_uuid': role.uuid_id,
                'web_username': web_username,
                'run_action': self.run_action,
                'run_type': self.run_type,
                'isTemplate': True
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result




