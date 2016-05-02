# coding:utf-8
from django.conf.urls import patterns,url
from assetManage.views import *

urlpatterns = patterns('',
    url(r'^add/$', asset_add, name='asset_add'),
    url(r"^add_batch/$", asset_add_batch, name='asset_add_batch'),
    url(r'^list/$', asset_list, name='asset_list'),
    url(r'^start_up/$', asset_start_up, name='start_up'),
    url(r'^restart/$', asset_restart, name='restart'),
    url(r'^shutdown/$', asset_shutdown, name='shutdown'),
    url(r'^del/$', asset_del, name='asset_del'),
    url(r"^detail/$", asset_detail, name='asset_detail'),
    url(r'^edit/$', asset_edit, name='asset_edit'),
    url(r'^edit_batch/$', asset_edit_batch, name='asset_edit_batch'),
    url(r'^update/$', asset_update, name='asset_update'),
    url(r'^update_batch/$', asset_update_batch, name='asset_update_batch'),
    url(r'^upload/$', asset_upload, name='asset_upload'),
    url(r'^group/del/$', group_del, name='asset_group_del'),
    url(r'^group/add/$', group_add, name='asset_group_add'),
    url(r'^group/list/$', group_list, name='asset_group_list'),
    url(r'^group/edit/$', group_edit, name='asset_group_edit'),
    url(r'^idc/add/$', idc_add, name='idc_add'),
    url(r'^idc/list/$', idc_list, name='idc_list'),
    url(r'^idc/edit/$', idc_edit, name='idc_edit'),
    url(r'^idc/del/$', idc_del, name='idc_del'),
)