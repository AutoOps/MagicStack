#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2016 MagicStack
#
#   Licensed under the Apache License, Version 2.0 (the "License");
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


import datetime
import json
from django.db import models

from proxyManage.models import Proxy


class Backup(models.Model):
    STATUS = (
        ('00', '启用'),
        ('01', '暂停'),
        ('02', '销毁')
    )

    TYPES = (
        ('file', '文件备份'),
        ('path', '目录备份'),
        ('db', '数据库备份')
    )

    proxy = models.ForeignKey(Proxy, help_text="proxy")
    type = models.CharField(max_length=2, choices=TYPES, default='file', help_text='备份类型')
    kwargs = models.CharField(max_length=2000, help_text='备份参数')
    status = models.CharField(max_length=2, choices=STATUS, default='00', help_text='备份状态')
    b_trigger = models.CharField(max_length=100, help_text='备份触发器')
    create_time = models.DateField(help_text='创建时间', null=True)
    comment = models.TextField(blank=True, null=True, help_text='备注')

    task_uuid = models.CharField(max_length=100, null=True, help_text='备份任务ID')
    last_exec_time = models.CharField(max_length=100, null=True, help_text="最后执行时间")
    is_get_last = models.CharField(max_length=4, default='00', help_text="是否获取最后执行时间")

    ext1 = models.CharField(max_length=2000, null=True, help_text="扩展字段1")
    ext2 = models.CharField(max_length=2000, null=True, help_text="扩展字段2")
    ext3 = models.CharField(max_length=2000, null=True, help_text="扩展字段3")


    def to_dict(self):
        d = dict()
        for f in self._meta.fields:
            d[f.name] = getattr(self, f.name, None)
            if isinstance(d[f.name], (datetime.datetime, datetime.date)):
                d[f.name] = getattr(self, f.name, None).strftime('%Y-%m-%d %H:%M:%S')
        return d
