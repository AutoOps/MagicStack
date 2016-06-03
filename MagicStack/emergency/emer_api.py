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
from emergency.models import EmergencyType
from MagicStack.api import logger, CRYPTOR


def send_email(email_config,email_title, email_to, email_msg):
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


