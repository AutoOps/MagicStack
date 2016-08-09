# -*- coding:utf-8 -*-
from django.db import models
from userManage.models import User
import time


class Log(models.Model):
    """
    资产连接操做日志
    """
    user = models.CharField(max_length=20, null=True)
    host = models.CharField(max_length=200, null=True)
    remote_ip = models.CharField(max_length=100)
    login_type = models.CharField(max_length=100)
    log_path = models.CharField(max_length=100)
    start_time = models.DateTimeField(null=True)
    pid = models.IntegerField(null=True)
    is_finished = models.BooleanField(default=False)
    end_time = models.DateTimeField(null=True)
    filename = models.CharField(max_length=40, null=True)
    proxy_log_id = models.IntegerField()
    proxy_name = models.CharField(max_length=100)
    asset_id_unique = models.CharField(max_length=200)

    def __unicode__(self):
        return self.log_path


class TtyLog(models.Model):
    log = models.ForeignKey(Log)
    datetime = models.DateTimeField(auto_now=True)
    cmd = models.CharField(max_length=200)


class ExecLog(models.Model):
    """
    批量执行命令日志
    """
    remote_id = models.IntegerField(help_text=u'proxy上的log的ID')
    user = models.CharField(max_length=100)
    host = models.TextField()
    proxy_host = models.CharField(max_length=100, help_text=u'proxy的IP地址')
    cmd = models.TextField()
    remote_ip = models.CharField(max_length=100)
    result = models.TextField(default='')
    datetime = models.DateTimeField(auto_now=True)


class FileLog(models.Model):
    user = models.CharField(max_length=100)
    host = models.TextField()
    filename = models.TextField()
    type = models.CharField(max_length=20)
    remote_ip = models.CharField(max_length=100)
    result = models.TextField(default='')
    datetime = models.DateTimeField(auto_now=True)


class TermLog(models.Model):
    user = models.ManyToManyField(User)
    logPath = models.TextField()
    filename = models.CharField(max_length=40)
    logPWD = models.TextField()
    nick = models.TextField(null=True)
    log = models.TextField(null=True)
    history = models.TextField(null=True)
    timestamp = models.IntegerField(default=int(time.time()))
    datetimestamp = models.DateTimeField(auto_now_add=True)
