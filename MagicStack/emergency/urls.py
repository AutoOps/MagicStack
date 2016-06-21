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

from django.conf.urls import url, patterns
from emergency.views import *

urlpatterns = patterns('',
            url(r'^media/list$', media_list, name='media_list'),
            url(r'^media/add$', media_add, name='media_add'),
            url(r'^media/edit$', media_edit, name='media_edit'),
            url(r'^media/del$', media_del, name='media_del'),
            url(r'^emergency/rule/$', emergency_rule, name='emergency_rule'),
            url(r'^emergency/edit/$', emergency_edit, name='emergency_edit'),
            url(r'^emergency/save/$', emergency_save, name='emergency_save'),
            url(r'^emergency/event/$', emergency_event, name='emergency_event'),
)