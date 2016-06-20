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

import json
from django.db.models import Q

from MagicStack.api import *
from userManage.user_api import user_operator_record

from datetime import datetime
from models import *


# -*- coding:utf-8 -*-
from django.db.models import Q
from MagicStack.api import *
from models import *
from common.interface import APIRequest
from userManage.user_api import user_operator_record
from proxyManage.models import Proxy
from datetime import datetime
import json


@require_role('admin')
def task_list(request):
    """
        查看task
    """
    header_title, path1, path2 = u'常规任务', u'任务管理', u'常规任务'
    keyword = request.GET.get('search', '')
    task_lists = Task.objects.all().exclude(task_statu='02').order_by('create_time')

    if keyword:
        task_lists = task_lists.filter(Q(task_type__icontains=keyword) | Q(create_time__icontains=keyword))

    task_lists, p, tasks, page_range, current_page, show_first, show_end = pages(task_lists, request)
    return my_render('taskManage/task_list.html', locals(), request)


@require_role('admin')
@user_operator_record
def task_add(request, res, *args):
    if request.method == 'POST':
        param = {}
        # 触发器
        trigger_kwargs = request.POST.get('trigger')
        task_name = request.POST.get('task_type')
        module_name = request.POST.get('module_name')
        module_args = request.POST.get('task_kwargs') or ""
        task_host = request.POST.get('task_host')
        proxy = request.POST.get('proxy')
        comment = request.POST.get('comment')
        try:

            hosts = []
            # 没有选中主机，则认为是全选，取选中proxy下的所有
            proxy_obj = Proxy.objects.get(id=proxy)
            module_obj = Module.objects.get(id=module_name)
            param['trigger_kwargs'] = json.loads(trigger_kwargs)
            param['task_name'] = task_name
            task_kwargs = {}
            task_kwargs['module_name'] = module_obj.module_name
            task_kwargs['module_args'] = module_args

            if not task_host:
                hosts = Asset.objects.all().filter(proxy=proxy_obj)
                if not hosts:
                    # 没有可执行主机
                    raise ServerError("no exec host")
            else:
                for host_id in task_host:
                    hosts.append(Asset.objects.get(id=host_id))

            host_list = []
            resource = []
            # 构建inventory 和 构建主机list
            for host in hosts:
                host_list.append(host.networking.all()[0].ip_address)
                tmp_d = dict()
                tmp_d['hostname'] = host.networking.all()[0].ip_address
                tmp_d['port'] = host.port
                tmp_d['username'] = host.username
                tmp_d['password'] = CRYPTOR.decrypt(host.password)
                resource.append(tmp_d)
            task_kwargs['host_list'] = host_list
            task_kwargs['resource'] = resource
            param['task_kwargs'] = task_kwargs
            # 调用proxy接口，创建任务
            api = APIRequest('{0}/v1.0/job'.format(proxy_obj.url), proxy_obj.username,
                             CRYPTOR.decrypt(proxy_obj.password))
            result, code = api.req_post(json.dumps(param))
            if code != 200:
                raise ServerError(result)
            else:
                task = Task(task_type=task_name, task_proxy=proxy, task_kwargs=json.dumps(task_kwargs),
                            trigger_kwargs=json.dumps(trigger_kwargs), channal='00', comment=comment,
                            task_uuid=result['job']['job_id'], create_time=datetime.now())
                task.save()
        except ServerError, e:
            error = e.message
            res['flag'] = False
            res['content'] = error
        except Exception, e:
            res['flag'] = False
            res['content'] = e[1]
        else:
            res['flag'] = True
        return HttpResponse(json.dumps(res))
    elif request.method == "GET":
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        res['proxys'] = proxy_list
        res['task_types'] = Task.TYPES
        return HttpResponse(json.dumps(res))


# 查询类定义
@require_role('admin')
def task_group(request):
    """
        根据task类型返回groups
    """
    task_type = request.POST.get('task_type')
    # 获取所有可用模块的所在分组，并根据组名排序

    groups = Module.objects.all().filter(task_type=task_type, module_statu='00').values(
        'group_name').distinct().order_by('group_name')
    return HttpResponse(json.dumps(list(groups)))


@require_role('admin')
def task_modules(request):
    """
        根据group类型，返回group所有可执行module
    """
    group_name = request.POST.get('group_name')
    # 根据指定组名获取所有模块，并根据组名、模块名称排序
    modules = [module.to_dict() for module in
               Module.objects.all().filter(group_name=group_name, module_statu='00').order_by('group_name',
                                                                                              'module_name')]
    return HttpResponse(json.dumps(modules))


@require_role('admin')
def task_module(request):
    """
        根据指定模块，返回模块信息
    """
    module_id = request.POST.get('module_id')
    module = Module.objects.get(id=module_id)
    return HttpResponse(json.dumps(module.comment))

