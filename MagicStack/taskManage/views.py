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
import urllib2
import traceback

from django.db.models import Q
from django.shortcuts import render

from MagicStack.api import *
from models import *
from common.interface import APIRequest
from userManage.user_api import user_operator_record
from proxyManage.models import Proxy
from datetime import datetime


@require_role('admin')
def task_list(request):
    """
        查看task
    """
    header_title, path1, path2 = u'常规任务', u'任务管理', u'常规任务'
    keyword = request.GET.get('search', '')
    task_lists = Task.objects.all().exclude(task_statu='02').order_by('-id')
    d_states = dict(Task.STATUS)
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
            # 构建trigger
            trigger_kwargs = json.loads(trigger_kwargs)
            start_date = trigger_kwargs.pop('start_date')
            if not trigger_kwargs:
                start_date_2_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                trigger_kwargs['year'] = start_date_2_date.year
                trigger_kwargs['month'] = start_date_2_date.month
                trigger_kwargs['day'] = start_date_2_date.day
                trigger_kwargs['hour'] = start_date_2_date.hour
                trigger_kwargs['minute'] = start_date_2_date.minute
                trigger_kwargs['second'] = start_date_2_date.second
            trigger_kwargs['start_date'] = start_date
            param['trigger_kwargs'] = trigger_kwargs

            hosts = []
            # 没有选中主机，则认为是全选，取选中proxy下的所有
            proxy_obj = Proxy.objects.get(id=proxy)
            module_obj = Module.objects.get(id=module_name)
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
                raise ServerError(result['messege'])
            else:
                task = Task(task_type=task_name, task_proxy=proxy_obj, task_kwargs=json.dumps(task_kwargs),
                            trigger_kwargs=json.dumps(trigger_kwargs), channal='00', comment=comment,
                            task_uuid=result['job']['job_id'], create_time=datetime.now(), module=module_obj)
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


@require_role('admin')
@user_operator_record
def task_action(request, res, *args, **kwargs):
    if request.method == 'POST':

        task_id = request.POST.get('task_id')
        action = request.POST.get('action')
        task = Task.objects.get(id=task_id)
        try:
            # TODO 先获取记录是否存在，存在的话就是新建

            # 构建参数
            param = {'action': action}

            # 调用proxy接口，
            api = APIRequest('{0}/v1.0/job/{1}/action/'.format(task.task_proxy.url, task.task_uuid),
                             task.task_proxy.username,
                             CRYPTOR.decrypt(task.task_proxy.password))
            result, code = api.req_post(json.dumps(param))
            if code != 200:
                raise ServerError(result['messege'])
            else:
                if action == 'pause':
                    task.task_statu = '01'
                else:
                    task.task_statu = '00'
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


@require_role('admin')
@user_operator_record
def task_del(request, res, *args, **kwargs):
    if request.method == 'POST':
        task_ids = request.POST.get('task_id')
        logger.info("task_id   %s" % task_ids)
        res['flag'] = True
        success = []
        fail = []
        # 循环删除
        for task_id in task_ids.split(','):
            task = Task.objects.get(id=task_id)
            try:
                # 调用proxy接口，
                api = APIRequest('{0}/v1.0/job/{1}'.format(task.task_proxy.url, task.task_uuid),
                                 task.task_proxy.username,
                                 CRYPTOR.decrypt(task.task_proxy.password))
                result, code = api.req_del(json.dumps({}))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    task.task_statu = '02'
                    task.save()
            except ServerError, e:
                fail.append(task)
                error = e.message
                res['flag'] = False
                res['content'] = error
            except Exception, e:
                fail.append(task)
                res['flag'] = False
                res['content'] = e[1]
            else:
                success.append(task)
        if len(success) + len(fail) > 1:
            res['content'] = 'success [%d] fail [%d]' % (len(success), len(fail))

        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def task_exec_info_v1(request, res, *args, **kwargs):
    """
        获取任务执行信息

        前端使用jquery plugin datatables进行分页
        后端根据前端规则组合数据
    """

    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        page = request.POST.get('page')
        limit = request.POST.get('limit')
        task = Task.objects.get(id=task_id)
        try:
            # 调用proxy接口，
            api = APIRequest('{0}/v1.0/job_task/{1}'.format(task.task_proxy.url, task.task_uuid),
                             task.task_proxy.username,
                             CRYPTOR.decrypt(task.task_proxy.password))
            result, code = api.req_get()
            if code != 200:
                raise ServerError(result['messege'])
            else:
                tasks = result['result']['tasks']
        except ServerError, e:
            error = e.message
            res['flag'] = False
            res['content'] = error
        except Exception, e:
            res['flag'] = False
            res['content'] = e[1]
        else:
            res['flag'] = True
            res['tasks'] = tasks

        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def task_exec_info(request, res, *args, **kwargs):
    """
        获取任务执行信息

        前端使用jquery plugin datatables进行分页
        后端根据前端规则组合数据
    """

    if request.method == 'POST':
        # 初始化返回结果
        return_obj = {
            "sEcho": request.POST.get('sEcho', 0), # 前端上传原样返回
            "iTotalRecords": 0, # 总记录数
            "iTotalDisplayRecords": 0, # 过滤后总记录数
            "aaData": [] # 返回前端数据，json格式
        }

        # 获取过滤条件
        task_id = request.POST.get('task_id')
        # 前端datatable上传每页显示数据
        limit = request.POST.get('iDisplayLength', 0)
        # 前端datatable上送从第几条开始展示
        offset = request.POST.get('iDisplayStart', 5)
        task = Task.objects.get(id=task_id)

        # 获取数据
        try:
            # 调用proxy接口，
            api = APIRequest(
                '{0}/v1.0/job_task/{1}?limit={2}&offset={3}'.format(task.task_proxy.url, task.task_uuid, limit, offset),
                task.task_proxy.username,
                CRYPTOR.decrypt(task.task_proxy.password))
            result, code = api.req_get()
            if code != 200:
                raise ServerError(result['messege'])
            else:
                tasks = result['result']['tasks']
                total_count = result['result']['total_count']
                display_lsit = []
                for task in tasks:
                    display_lsit.append({
                        'start_time': task.get('start_time'),
                        'end_time': task.get('end_time'),
                        'status': task.get('status'),
                        'id': task.get('id'),
                        'job_id': task.get('job_id')
                    })

                return_obj['aaData'] = display_lsit
                return_obj['iTotalRecords'] = total_count
                return_obj['iTotalDisplayRecords'] = total_count
                logger.info(">>>>>>{0}".format(return_obj))
        except:
            logger.error("GET TASK EXEC INFO ERROR\n {0}".format(traceback.format_exc()))

        return HttpResponse(json.dumps(return_obj))


@require_role('admin')
def task_exec_replay(request):
    """
        task 回放
    """
    if request.method == "POST":
        try:
            task_id = request.REQUEST.get('task_id', None)
            job_id = request.REQUEST.get('job_id', None)
            job = Task.objects.filter(task_uuid=job_id).first()
            url = '{0}/v1.0/job_task_replay/{1}'.format(job.task_proxy.url, task_id)
            content = json.load(urllib2.urlopen(url)).get('content')
            return HttpResponse(content)
        except:
            import traceback

            logger.error(traceback.format_exc())
            return HttpResponse({})
    elif request.method == 'GET':
        return render(request, 'logManage/record.html')

    else:
        return HttpResponse("ERROR METHOD!")

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



