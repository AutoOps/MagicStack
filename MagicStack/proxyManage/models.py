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


class Proxy(models.Model):
    proxy_name = models.CharField(max_length=90, unique=True, help_text='proxy名字')
    username = models.CharField(max_length=90, help_text='proxy用户名')
    password = models.CharField(max_length=200, help_text='proxy用户密码')
    url = models.URLField(max_length=100, help_text='api地址')
    create_time = models.DateField()
    comment = models.TextField(blank=True, help_text='备注')

    def __unicode__(self):
        return self.proxy_name


    def to_dict(self):
        d = dict()
        for f in self._meta.fields:
            d[f.name] = getattr(self, f.name, None)
            if isinstance(d[f.name], (datetime.datetime, datetime.date)):
                d[f.name] = getattr(self, f.name, None).strftime('%Y-%m-%d %H:%M:%S')
        return d