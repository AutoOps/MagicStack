# coding:utf-8
from django.conf.urls import patterns,url
from assetManage.views import *

urlpatterns = patterns('',
    url(r'^add/$', asset_add, name='asset_add'),
    url(r'^list/$', asset_list, name='asset_list'),
    url(r'^action/(\w+)/$', asset_action, name='asset_action'),
    url(r'^event/$', asset_event, name='asset_event'),
    url(r'^del/$', asset_del, name='asset_del'),
    url(r"^detail/$", asset_detail, name='asset_detail'),
    url(r'^edit/$', asset_edit, name='asset_edit'),
    url(r'^update_batch/$', asset_update_batch, name='asset_update_batch'),
    url(r'^group/del/$', group_del, name='asset_group_del'),
    url(r'^group/add/$', group_add, name='asset_group_add'),
    url(r'^group/list/$', group_list, name='asset_group_list'),
    url(r'^group/edit/$', group_edit, name='asset_group_edit'),
    url(r'^idc/add/$', idc_add, name='idc_add'),
    url(r'^idc/list/$', idc_list, name='idc_list'),
    url(r'^idc/edit/$', idc_edit, name='idc_edit'),
    url(r'^idc/del/$', idc_del, name='idc_del'),
)