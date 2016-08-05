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
from django.db import models
from proxyManage.models import Proxy


class File(models.Model):

    STATUS = (
        ('00', '上传中'),
        ('01', '完成'),
    )

    proxy = models.ForeignKey(Proxy, help_text="proxy")
    create_time = models.DateTimeField(help_text='创建时间', null=True)
    task_uuid = models.CharField(max_length=100, null=True, help_text='上传任务ID')
    path = models.CharField(max_length=200, null=True, help_text="上传路径")
    result = models.TextField(null=True, help_text="上传结果")
    status = models.CharField(max_length=2, choices=STATUS, default='00', help_text='上传状态')


    def to_dict(self):
        d = dict()
        for f in self._meta.fields:
            d[f.name] = getattr(self, f.name, None)
            if isinstance(d[f.name], (datetime.datetime, datetime.date)):
                d[f.name] = getattr(self, f.name, None).strftime('%Y-%m-%d %H:%M:%S')
        return d
