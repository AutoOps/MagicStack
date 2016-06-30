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

from django.conf.urls import patterns, url
from backupManage.views import *


urlpatterns = patterns('',
    url(r'^dbbackup_list/$', dbbackup_list, name='dbbackup_list'),
    url(r'^filebackup_list/$', dbbackup_list, name='filebackup_list'),
    url(r'^pathbackup_list/$', dbbackup_list, name='pathbackup_list'),
    url(r'^dbbackup_add/$', dbbackup_add, name='dbbackup_add'),
    url(r'^dbbackup_del/$', dbbackup_del, name='dbbackup_del'),
    url(r'^dbbackup_edit/$', dbbackup_edit, name='dbbackup_edit'),

    # 备份回放公共部分
    url(r'^backup_exec_replay/$', backup_exec_replay, name='backup_exec_replay'),
    url(r'^backup_exec_info/$', backup_exec_info, name='backup_exec_info'),


)
