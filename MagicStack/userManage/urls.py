from django.conf.urls import patterns, include, url
from MagicStack.api import view_splitter
from userManage.views import *

urlpatterns = patterns('userManage.views',
                       url(r'^group/add/$', 'group_add', name='user_group_add'),
                       url(r'^group/list/$', 'group_list', name='user_group_list'),
                       url(r'^group/del/$', 'group_del', name='user_group_del'),
                       url(r'^group/edit/$', 'group_edit', name='user_group_edit'),
                       url(r'^add/$', 'user_add', name='user_add'),
                       url(r'^del/$', 'user_del', name='user_del'),
                       url(r'^list/$', 'user_list', name='user_list'),
                       url(r'^edit/$', 'user_edit', name='user_edit'),
                       url(r'^detail/$', 'user_detail', name='user_detail'),
                       url(r'^profile/$', 'profile', name='user_profile'),
                       url(r'^update/$', 'change_info', name='user_update'),
                       url(r'^mail/retry/$', 'send_mail_retry', name='mail_retry'),
                       url(r'^password/reset/$', 'reset_password', name='password_reset'),
                       url(r'^login/password/forget/$', 'forget_password', name='password_forget'),
                       url(r'^key/gen/$', 'regen_ssh_key', name='key_gen'),
                       )
