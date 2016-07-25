# -*- coding:utf-8 -*-
__author__ = 'majing'

from django.db import models
from django.contrib.auth.models import AbstractUser


class UserGroup(models.Model):
    name = models.CharField(max_length=80, unique=True)
    comment = models.CharField(max_length=160, blank=True, null=True)

    def __unicode__(self):
        return self.name


class User(AbstractUser):
    USER_ROLE_CHOICES = (
        ('SU', 'SuperUser'),
        ('GA', 'GroupAdmin'),
        ('CU', 'CommonUser'),
    )
    uuid_id = models.CharField(max_length=200, verbose_name=u'uuid 唯一标示符')
    role = models.CharField(max_length=2, choices=USER_ROLE_CHOICES, default='CU')
    group = models.ManyToManyField(UserGroup)
    ssh_key_pwd = models.CharField(max_length=200)

    def __unicode__(self):
        return self.username


class UserOperatorRecord(models.Model):
    username = models.CharField(max_length=50, help_text='用户名')
    operator = models.CharField(max_length=50, help_text='操作')
    content = models.TextField()
    op_time = models.DateTimeField()
    result = models.CharField(max_length=20, help_text='执行结果')




class AdminGroup(models.Model):
    """
    under the user control group
    用户可以管理的用户组，或组的管理员是该用户
    """

    user = models.ForeignKey(User)
    group = models.ForeignKey(UserGroup)

    def __unicode__(self):
        return '%s: %s' % (self.user.username, self.group.name)


