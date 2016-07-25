# -*- coding:utf-8 -*-
from django.db import models
from assetManage.models import Asset, AssetGroup
from userManage.models import User, UserGroup


class PermSudo(models.Model):
    uuid_id = models.CharField(max_length=200, verbose_name=u'唯一标识符')
    name = models.CharField(max_length=100, unique=True)
    date_added = models.DateTimeField(auto_now=True)
    commands = models.TextField()
    comment = models.CharField(max_length=100, null=True, blank=True, default='')

    def __unicode__(self):
        return self.name


class PermRole(models.Model):
    uuid_id = models.CharField(max_length=200, verbose_name=u'唯一标识符')
    name = models.CharField(max_length=100, unique=True)
    comment = models.CharField(max_length=100, null=True, blank=True, default='')
    password = models.CharField(max_length=128)
    key_content = models.TextField(null=True, blank=True, default='')
    date_added = models.DateTimeField(auto_now=True)
    sudo = models.ManyToManyField(PermSudo, related_name='perm_role')
    system_groups = models.CharField(max_length=200, null=True, blank=True, verbose_name=u'系统组')

    def __unicode__(self):
        return self.name


class PermRule(models.Model):
    date_added = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=100, unique=True)
    comment = models.CharField(max_length=100)
    asset = models.ManyToManyField(Asset, related_name='perm_rule')
    asset_group = models.ManyToManyField(AssetGroup, related_name='perm_rule')
    user = models.ManyToManyField(User, related_name='perm_rule')
    user_group = models.ManyToManyField(UserGroup, related_name='perm_rule')
    role = models.ManyToManyField(PermRole, related_name='perm_rule')

    def __unicode__(self):
        return self.name


class PermPush(models.Model):
    asset = models.ForeignKey(Asset, related_name='perm_push')
    role = models.ForeignKey(PermRole, related_name='perm_push')
    is_public_key = models.BooleanField(default=False)
    is_password = models.BooleanField(default=False)
    success = models.BooleanField(default=False)
    result = models.TextField(default='')
    date_added = models.DateTimeField(auto_now=True)

