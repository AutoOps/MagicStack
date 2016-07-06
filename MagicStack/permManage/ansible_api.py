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

    def push_key(self, user, key_path, proxy):
        """
        push the ssh authorized key to target.
        """
        module_args = 'user="%s" key="{{ lookup("file", "%s") }}" state=present' % (user, key_path)
        data = {'mod_name': 'authorized_key',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args,
                'role_name': user
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result

    def push_multi_key(self, **user_info):
        """
        push multi key
        :param user_info:
        :return:
        """
        ret_failed = []
        ret_success = []
        for user, key_path in user_info.iteritems():
            ret = self.push_key(user, key_path)
            if ret.get("status") == "ok":
                ret_success.append(ret)
            if ret.get("status") == "failed":
                ret_failed.append(ret)

        if ret_failed:
            return {"status": "failed", "msg": ret_failed}
        else:
            return {"status": "success", "msg": ret_success}

    def del_key(self, user, key_path, proxy):
        """
        push the ssh authorized key to target.
        """
        module_args = 'user="%s" key="{{ lookup("file", "%s") }}" state="absent"' % (user, key_path)
        # self.run("authorized_key", module_args, become=True)
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

    def add_user(self, username,proxy, password=''):
        """
        add a host user.
        """

        if password:
            encrypt_pass = sha512_crypt.encrypt(password)
            module_args = 'name=%s shell=/bin/bash password=%s' % (username, encrypt_pass)
        else:
            module_args = 'name=%s shell=/bin/bash' % username

        data = {'mod_name': 'user',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args,
                'role_name': username
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result

    def add_multi_user(self, **user_info):
        """
        add multi user
        :param user_info: keyword args
            {username: password}
        :return:
        """
        ret_success = []
        ret_failed = []
        for user, password in user_info.iteritems():
            ret = self.add_user(user, password)
            if ret.get("status") == "ok":
                ret_success.append(ret)
            if ret.get("status") == "failed":
                ret_failed.append(ret)

        if ret_failed:
            return {"status": "failed", "msg": ret_failed}
        else:
            return {"status": "success", "msg": ret_success}

    def del_user(self, username, proxy):
        """
        delete a host user.
        """
        module_args = 'name=%s state=absent remove=yes move_home=yes force=yes' % username
        # self.run("user", module_args, become=True)
        data = {'mod_name': 'user',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args,
                'role_name': username,
                'action': 'delete'
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result

    def del_user_sudo(self, username, proxy):
        """
        delete a role sudo item
        :param username:
        :return:
        """
        module_args = "sed -i 's/^%s.*//' /etc/sudoers" % username
        # self.run("command", module_args, become=True)
        data = {'mod_name': 'command',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args,
                'action': 'delete'
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result

    @staticmethod
    def gen_sudo_script(role_list, sudo_list):
        sudo_alias = {}
        sudo_user = {}
        for sudo in sudo_list:
            sudo_alias[sudo.name] = sudo.commands

        for role in role_list:
            sudo_user[role.name] = ','.join(sudo_alias.keys())

        sudo_j2 = get_template('permManage/role_sudo.j2')
        sudo_content = sudo_j2.render(Context({"sudo_alias": sudo_alias, "sudo_user": sudo_user}))
        sudo_file = NamedTemporaryFile(delete=False)
        sudo_file.write(sudo_content)
        sudo_file.close()
        return sudo_file.name

    def push_sudo_file(self, role_list, sudo_list, proxy):
        """
        use template to render pushed sudoers file
        :return:
        """
        module_args = self.gen_sudo_script(role_list, sudo_list)
        # self.run("script", module_args1, become=True)
        data = {'mod_name': 'script',
                'resource': self.resource,
                'hosts': self.host_list,
                'mod_args': module_args
                }
        data = json.dumps(data)
        api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
        result, code = api.req_post(data)
        return result




