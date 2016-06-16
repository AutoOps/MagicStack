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


from django.db import models


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

    backup_proxy = models.CharField(max_length=254, unique=True, help_text='备份proxy')
    backup_host = models.CharField(max_length=254, unique=True, help_text='备份proxy')
    backup_type = models.CharField(max_length=2, choices=TYPES, default='file', help_text='备份类型')
    backup_kwargs = models.CharField(max_length=254, help_text='备份参数')
    backup_cycle = models.CharField(max_length=100, help_text='备份周期')
    backup_status = models.CharField(max_length=2, choices=STATUS, default='00', help_text='备份状态')
    task_uuid = models.CharField(max_length=100, help_text='备份任务ID')
    create_time = models.DateField(help_text='创建时间')
    comment = models.TextField(blank=True, help_text='备注')

    def __unicode__(self):
        return self.proxy_name


