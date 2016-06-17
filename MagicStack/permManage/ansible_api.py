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



class AnsibleError(StandardError):
    """
    the base AnsibleError which contains error(required),
    data(optional) and message(optional).
    存储所有Ansible 异常对象
    """
    def __init__(self, error, data='', message=''):
        super(AnsibleError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message


class CommandValueError(AnsibleError):
    """
    indicate the input value has error or invalid. 
    the data specifies the error field of input form.
    输入不合法 异常对象
    """
    def __init__(self, field, message=''):
        super(CommandValueError, self).__init__('value:invalid', field, message)





    @property
    def results(self):
        """
        {'failed': {'localhost': ''}, 'ok': {'jumpserver': ''}}
        """
        result = {'failed': {}, 'ok': {}}
        dark = self.results_raw.get('dark')
        contacted = self.results_raw.get('contacted')
        if dark:
            for host, info in dark.items():
                result['failed'][host] = info.get('msg')

        if contacted:
            for host, info in contacted.items():
                if info.get('invocation').get('module_name') in ['raw', 'shell', 'command', 'script']:
                    if info.get('rc') == 0:
                        result['ok'][host] = info.get('stdout') + info.get('stderr')
                    else:
                        result['failed'][host] = info.get('stdout') + info.get('stderr')
                else:
                    if info.get('failed'):
                        result['failed'][host] = info.get('msg')
                    else:
                        result['ok'][host] = info.get('changed')
        return result




    @property
    def result(self):
        result = {}
        for k, v in self.results_raw.items():
            if k == 'dark':
                for host, info in v.items():
                    result[host] = {'dark': info.get('msg')}
            elif k == 'contacted':
                for host, info in v.items():
                    result[host] = {}
                    if info.get('stdout'):
                        result[host]['stdout'] = info.get('stdout')
                    elif info.get('stderr'):
                        result[host]['stderr'] = info.get('stderr')
        return result

    @property
    def state(self):
        result = {}
        if self.stdout:
            result['ok'] = self.stdout
        if self.stderr:
            result['err'] = self.stderr
        if self.dark:
            result['dark'] = self.dark
        return result

    @property
    def exec_time(self):
        """
        get the command execute time.
        """
        result = {}
        all = self.results_raw.get("contacted")
        for key, value in all.iteritems():
            result[key] = {
                    "start": value.get("start"),
                    "end"  : value.get("end"),
                    "delta": value.get("delta"),}
        return result

    @property
    def stdout(self):
        """
        get the comamnd standard output.
        """
        result = {}
        all = self.results_raw.get("contacted")
        for key, value in all.iteritems():
            result[key] = value.get("stdout")
        return result

    @property
    def stderr(self):
        """
        get the command standard error.
        """
        result = {}
        all = self.results_raw.get("contacted")
        for key, value in all.iteritems():
            if value.get("stderr") or value.get("warnings"):
                result[key] = {
                    "stderr": value.get("stderr"),
                    "warnings": value.get("warnings"),}
        return result

    @property
    def dark(self):
        """
        get the dark results.
        """
        return self.results_raw.get("dark")


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
        # receive role_list = [role1, role2] sudo_list = [sudo1, sudo2]
        # return sudo_alias={'NETWORK': '/sbin/ifconfig, /ls'} sudo_user={'user1': ['NETWORK', 'SYSTEM']}
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

    @property
    def raw_results(self):
        """
        get the raw results after playbook run.
        """
        return self.results



if __name__ == "__main__":

    resource = [{"hostname": "127.0.0.1", "port": "22", "username": "yumaojun", "password": "yusky0902",
                 }]
    cmd = Command(resource)
    print cmd.run('ls')


