# -*- coding:utf-8 -*-
# Copyright (c) 2016 MagicStack
#
# Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import smtplib
from email.mime.text import MIMEText
from email.header import Header
import requests
import json
from MagicStack.api import logger, CRYPTOR


def send_email(email_config,email_title, email_to, email_msg):
    """
    发送邮件
    """
    message = MIMEText(email_msg, 'plain', 'utf-8')
    message['Subject'] = Header(email_title)
    message['From'] = email_config.email_username
    emali_list = ','.join(email_to)
    message['To'] = emali_list
    server = smtplib.SMTP()
    if email_config.email_use_ssl:
        server = smtplib.SMTP_SSL()
    try:
        server.connect(email_config.smtp_server, email_config.smtp_server_port)
        if email_config.email_use_tls and email_config.email_use_ssl is not True:
            server.starttls()
        server.login(email_config.email_username, CRYPTOR.decrypt(email_config.email_password))
        server.sendmail(email_config.email_username, email_to, message.as_string())
    except Exception as e:
        logger.error(e)
    finally:
        server.quit()


def send_wx_mail(corpid, corpsecret,param):
    get_token = requests.get('https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={0}&corpsecret={1}'.format(corpid, corpsecret),verify=False)
    res_token = get_token.json()
    if 'access_token' in res_token:
        access_token = res_token['access_token']
        param = {
            "touser": "@all",
            "toparty": "1",
            "totag": "@all",
            "msgtype": "text",
            "agentid": 1,
            "text": {
                "content": "hello world"
            },
            "safe": "0"
        }
        body = json.dumps(param)
        res = requests.post('https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={0}'.format(access_token),
                            data=body, verify=False)
        rest = res.json()    #{'errcode':0, 'errmsg':'ok'}
        return rest
    else:
        return res_token

if __name__ == '__main__':
    msg = send_wx_mail('wxaf46979b678a2fce', '-NG1TBtm08G55eU2G60KheOA5KpqnISqRz15JeomZICCMIMePF2O_d3u3_NJlqeF', '')
    print "send_wx_msg:%s"%msg
