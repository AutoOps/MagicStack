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


class Task(models.Model):
    TYPES = (
        ('ansible', "Ansible Play"),
        ('ansible-pb', "Ansible Playbook"),
    )

    STATUS = (
        ('00', '启用'),
        ('01', '暂停'),
        ('02', '销毁')
    )

    task_proxy = models.CharField(max_length=2000, help_text='备份proxy')
    task_type = models.CharField(max_length=20, choices=TYPES, help_text="任务类型")
    task_kwargs = models.BinaryField(help_text="任务参数") # 字典
    task_statu = models.CharField(max_length=2, choices=STATUS, default='00', help_text="任务状态")
    trigger_kwargs = models.BinaryField(help_text="触发器参数") # 字典
    create_time = models.DateField(help_text="创建时间")
    comment = models.TextField(blank=True, help_text="备注")
    task_uuid = models.CharField(max_length=100, help_text="任务ID")



