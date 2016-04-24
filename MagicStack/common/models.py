#! /usr/bin/env python
# -*- coding:utf-8 -*-

from django.db import models


class Task(models.Model):
    name = models.CharField(max_length=50, verbose_name='task name')
    username = models.CharField(max_length=50, verbose_name=u'网站用户的名字')
    status = models.CharField(max_length=50, verbose_name='status')
    url = models.CharField(max_length=100, verbose_name='api url')
    content = models.TextField()
    start_time = models.DateTimeField()

    class Meta:
        ordering = ['-start_time']