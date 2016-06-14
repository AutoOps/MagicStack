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

from django.db.models import Q
from MagicStack.api import *
from models import *
from userManage.user_api import user_operator_record
from datetime import datetime
import json


@require_role('admin')
def dbbackup_list(request):
    """
        查看数据库备份
    """
    header_title, path1, path2 = u'查看代理', u'代理管理', u'查看代理'
    keyword = request.GET.get('search', '')
    proxy_lists = Proxy.objects.all().order_by('create_time')
    proxy_id = request.GET.get('id', '')
    if keyword:
        proxy_lists = proxy_lists.filter(Q(name__icontains=keyword) | Q(create_time__icontains=keyword))

    if proxy_id:
        proxy_lists = proxy_lists.filter(id=int(proxy_id))
    print proxy_lists
    proxy_lists, p, proxys, page_range, current_page, show_first, show_end = pages(proxy_lists, request)
    return my_render('proxyManage/task_list.html', locals(), request)


@require_role('admin')
def filebackup_list(request):
    """
        查看文件备份
    """
    header_title, path1, path2 = u'查看代理', u'代理管理', u'查看代理'
    keyword = request.GET.get('search', '')
    proxy_lists = Proxy.objects.all().order_by('create_time')
    proxy_id = request.GET.get('id', '')

    if keyword:
        proxy_lists = proxy_lists.filter(Q(name__icontains=keyword) | Q(create_time__icontains=keyword))

    if proxy_id:
        proxy_lists = proxy_lists.filter(id=int(proxy_id))

    proxy_lists, p, proxys, page_range, current_page, show_first, show_end = pages(proxy_lists, request)
    return my_render('proxyManage/task_list.html', locals(), request)


@require_role('admin')
def pathbackup_list(request):
    """
        查看目录备份
    """
    header_title, path1, path2 = u'查看代理', u'代理管理', u'查看代理'
    keyword = request.GET.get('search', '')
    proxy_lists = Proxy.objects.all().order_by('create_time')
    proxy_id = request.GET.get('id', '')

    if keyword:
        proxy_lists = proxy_lists.filter(Q(name__icontains=keyword) | Q(create_time__icontains=keyword))

    if proxy_id:
        proxy_lists = proxy_lists.filter(id=int(proxy_id))

    proxy_lists, p, proxys, page_range, current_page, show_first, show_end = pages(proxy_lists, request)
    return my_render('proxyManage/task_list.html', locals(), request)


@require_role('admin')
@user_operator_record
def dbbackup_add(request, res, *args):
    error = msg = ''
    header_title, path1, path2 = u'添加代理', u'代理管理', u'添加代理'
    res['operator'] = path2
    if request.method == 'POST':
        proxy_name = request.POST.get('proxy_name', '')
        user_name = request.POST.get('user_name', '')
        password = request.POST.get('user_password', '')
        proxy_url = request.POST.get('proxy_url', '')
        comment = request.POST.get('comment', '')
        encrypt = CRYPTOR.encrypt(password)
        try:
            if not proxy_name:
                raise ServerError(u'Proxy名不能为空')
            if Proxy.objects.filter(proxy_name=proxy_name):
                raise ServerError(u'Proxy名已存在')

        except ServerError, e:
            error = e.message
            res['flag'] = False
            res['content'] = error
        else:

            create_time = datetime.now()
            Proxy.objects.create(proxy_name=proxy_name, username=user_name, password=encrypt,
                                 url=proxy_url, comment=comment, create_time=create_time)
            msg = u'添加Proxy[%s]成功' % proxy_name
            res['flag'] = True
            res['content'] = msg
        return HttpResponse(json.dumps(res))

    return my_render('proxyManage/proxy_add.html', locals(), request)


@require_role('admin')
@user_operator_record
def dbbackup_edit(request, res, *args):
    header_title, path1, path2 = u'编辑代理', u'代理管理', u'编辑代理'
    res['operator'] = path2
    id = request.GET.get('id', request.POST.get('proxy_id'))
    proxy = get_object(Proxy, id=id)
    if request.method == 'POST':
        proxy_name = request.POST.get('proxy_name')
        user_name = request.POST.get('user_name')
        password = request.POST.get('user_password')
        proxy_url = request.POST.get('proxy_url')
        comment = request.POST.get('comment', '')
        encrypt = CRYPTOR.encrypt(password)
        try:
            if not proxy_name:
                raise ServerError(u'Proxy名不能为空')

            if proxy.proxy_name != proxy_name and Proxy.objects.filter(proxy_name=proxy_name):
                raise ServerError(u'Proxy名已存在')

        except ServerError, e:
            res['flag'] = 'false'
            res['content'] = e.message
        else:
            proxy.proxy_name = proxy_name
            proxy.username = user_name
            proxy.password = encrypt
            proxy.url = proxy_url
            proxy.comment = comment
            proxy.save()
            msg = u'编辑Proxy[%s]成功' % proxy_name
            res['content'] = msg
        return HttpResponse(json.dumps(res))

    res['proxy_id'] = proxy.id
    res['proxy_name'] = proxy.proxy_name
    res['username'] = proxy.username
    res['password'] = CRYPTOR.decrypt(proxy.password)
    res['proxy_url'] = proxy.url
    res['comment'] = proxy.comment
    return HttpResponse(json.dumps(res))