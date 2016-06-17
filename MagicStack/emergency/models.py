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

from django.db import models
from userManage.models import User

MEDIA_TYPE = (
    (1, u'电子邮件'),
    (2, u'微信'),
    (3, u'短信')
)


class EmergencyType(models.Model):
    name = models.CharField(max_length=100, verbose_name=u'告警媒介名字')
    type = models.CharField(max_length=100, verbose_name=u'告警媒介类型')
    status = models.CharField(max_length=20, verbose_name=u'使用状态')
    detail = models.TextField(verbose_name=u'详情 ')
    smtp_server = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'发送邮件服务器')
    smtp_server_port = models.IntegerField(blank=True, null=True, verbose_name=u'服务器端口')
    email_username = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'邮件用户名')
    email_password = models.CharField(max_length=200,  blank=True, null=True, verbose_name=u'用户密码')
    email_use_tls = models.BooleanField(default=True)
    email_use_ssl = models.BooleanField(default=False)
    corpid = models.CharField(max_length=100, null=True, blank=True, verbose_name=u'微信企业号CorpID')
    corpsecret = models.CharField(max_length=252, null=True, blank=True, verbose_name=u'微信企业号secret')
    comment = models.TextField()

    def __unicode__(self):
        return self.name


class EmergencyRules(models.Model):

    EMER_CONTENT = (
        (1, u'用户变更'),
        (2, u'资产变更'),
        (3, u'应用变更'),
        (4, u'任务变更'),
        (5, u'备份变更'),
        (6, u'授权变更'),
        (7, u'代理变更')
    )
    TIME_TYPE = (
        (1, u'全部'),
        (2, u'工作日'),
        (3, u'周末')
    )

    RULE_STATUS = (
        (0, u'禁用'),
        (1, u'启用')
    )

    name = models.CharField(max_length=100, verbose_name=u'规则名称')
    content = models.IntegerField(choices=EMER_CONTENT, verbose_name=u'告警通知的内容')
    staff = models.ManyToManyField(User, verbose_name=u'告警通知人员')
    emergency_time = models.IntegerField(choices=TIME_TYPE, default=1)
    media_type = models.ForeignKey(EmergencyType, null=True)
    status = models.IntegerField(choices=RULE_STATUS, default=0)
    is_add = models.BooleanField(default=1)
    is_delete = models.BooleanField(default=1)
    is_update = models.BooleanField(default=1)

    def __unicode__(self):
        return self.name