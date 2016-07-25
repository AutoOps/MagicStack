# -*- coding: utf-8 -*-

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import os.path
import shutil
from paramiko import SSHException
from paramiko.rsakey import RSAKey
from MagicStack.api import mkdir
from uuid import uuid4
from MagicStack.api import CRYPTOR,logger
from MagicStack.settings import KEY_DIR


def get_rand_pass():
    """
    get a reandom password.
    """
    CRYPTOR.gen_rand_pass(20)


def updates_dict(*args):
    """
    surport update multi dict
    """
    result = {}
    for d in args:
        result.update(d)
    return result


def gen_keys(key=""):
    """
    生成公钥 私钥
    """
    output = StringIO.StringIO()
    sbuffer = StringIO.StringIO()
    key_content = {}
    if not key:
        try:
            key = RSAKey.generate(2048)
            key.write_private_key(output)
            private_key = output.getvalue()
        except IOError:
            raise IOError('gen_keys: there was an error writing to the file')
        except SSHException:
            raise SSHException('gen_keys: the key is invalid')
    else:
        private_key = key
        output.write(key)
        try:
            key = RSAKey.from_private_key(output)
        except SSHException, e:
            raise SSHException(e)

    for data in [key.get_name(),
                 " ",
                 key.get_base64(),
                 " %s@%s" % ("magicstack", os.uname()[1])]:
        sbuffer.write(data)
    public_key = sbuffer.getvalue()
    key_content['public_key'] = public_key
    key_content['private_key'] = private_key
    logger.info('gen_keys:   key content:%s'%key_content)
    return key_content


def trans_all(str):
    if str.strip().lower() == "all":
        return str.upper()
    else:
        return str

if __name__ == "__main__":
    print gen_keys()


