#! /usr/bin/env python
# -*- coding:utf-8 -*-

from django.db import models
import uuid


class Task(models.Model):
    task_name = models.CharField(max_length=50, help_text='task name')
    username = models.CharField(max_length=50, help_text=u'网站用户的名字')
    status = models.CharField(max_length=50, help_text='status')
    url = models.CharField(max_length=100, help_text='api url')
    content = models.TextField(help_text=u'详情')
    start_time = models.DateTimeField()
    proxy_name = models.CharField(max_length=200, null=True, help_text=u'代理名称')
    role_name = models.CharField(max_length=100, null=True, help_text=u'系统用户名')
    role_uuid = models.CharField(max_length=200, null=True, help_text=u'系统用户uuid')
    role_data = models.TextField(help_text=u'操作数据')
    action = models.CharField(max_length=10, null=True, help_text=u'操作 add update delete push')
    result = models.CharField(max_length=10, null=True, help_text=u'success or false')


    class Meta:
        ordering = ['-start_time']