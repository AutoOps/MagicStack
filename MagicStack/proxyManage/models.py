# -*- coding:utf-8 -*-
from django.db import models


class Proxy(models.Model):
    proxy_name = models.CharField(max_length=90, unique=True, help_text='proxy名字')
    username = models.CharField(max_length=90, help_text='proxy用户名')
    password = models.CharField(max_length=90, help_text='proxy用户密码')
    url = models.URLField(max_length=100, help_text='api地址')
    create_time = models.DateField()
    comment = models.TextField(blank=True, help_text='备注')

    def __unicode__(self):
        return self.proxy_name


