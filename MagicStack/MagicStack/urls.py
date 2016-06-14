"""MagicStack URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import patterns, include, url


urlpatterns = patterns('MagicStack.views',
    url(r'^$', 'index', name='index'),
    url(r'^skin_config/$', 'skin_config', name='skin_config'),
    url(r'^login/$', 'Login', name='login'),
    url(r'^logout/$', 'Logout', name='logout'),
    url(r'^exec_cmd/$', 'exec_cmd', name='exec_cmd'),
    url(r'^file/upload/$', 'upload', name='file_upload'),
    url(r'^file/download/$', 'download', name='file_download'),
    url(r'^setting', 'setting', name='setting'),
    url(r'^terminal/$', 'web_terminal', name='terminal'),
    url(r'^user/', include('userManage.urls')),
    url(r'^asset/', include('assetManage.urls')),
    url(r'^log/', include('logManage.urls')),
    url(r'^permission/', include('permManage.urls')),
    url(r'^proxy/', include('proxyManage.urls')),
    url(r'^task/', include('taskManage.urls')),
    url(r'^backup/', include('backupManage.urls')),
    url(r'^emergency/', include('emergency.urls')),
)

