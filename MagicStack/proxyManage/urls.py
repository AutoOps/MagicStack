# -*- coding:utf-8 -*-
from django.conf.urls import patterns, url
from proxyManage.views import *


urlpatterns = patterns('',
    url(r'^list/$', proxy_list, name='proxy_list'),
    url(r'^add/$', proxy_add, name='proxy_add'),
    url(r'^edit/$', proxy_edit, name='proxy_edit'),
    url(r'^del/$', proxy_del, name='proxy_del'),
    url(r"^get/hosts/$", get_host_for_proxy, name="get_host_for_proxy"),
)
