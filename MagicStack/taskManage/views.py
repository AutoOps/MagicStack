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
import re
import urllib2
import traceback

from django.db.models import Q
from django.shortcuts import render

from pygments.lexers import get_lexer_by_name
from pygments.formatters import get_formatter_by_name
from pygments import highlight

from MagicStack.api import *
from models import *
from common.interface import APIRequest
from userManage.user_api import user_operator_record
from assetManage.models import Asset
from proxyManage.models import Proxy
from datetime import datetime


@require_role('admin')
def task_list(request):
    """
        查看task
    """
    header_title, path1, path2 = u'常规任务', u'任务管理', u'常规任务'
    keyword = request.GET.get('search', '')
    task_lists = Task.objects.all().filter(task_type='ansible').exclude(task_statu='02').order_by('-id')
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
        task_host = request.POST.getlist('task_host[]') # 前端上送list时
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
                # 用于前端确定选择的asset
                tmp_d['id'] = host.id
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
            logger.error(traceback.format_exc())
            res['flag'] = False
            res['content'] = e[1]
        else:
            res['flag'] = True
        return HttpResponse(json.dumps(res))
    elif request.method == "GET":
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        res['proxys'] = proxy_list
        res['task_types'] = [Task.TYPES[0]]
        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def task_edit(request, res, *args, **kwargs):
    if request.method == 'POST':
        param = {}
        # 触发器
        trigger_kwargs = request.POST.get('trigger')
        comment = request.POST.get('comment')
        task_id = int(request.POST.get('task_id'))
        try:
            task = Task.objects.get(id=task_id)
            # 构建trigger
            trigger_kwargs = json.loads(trigger_kwargs)
            start_date = trigger_kwargs.pop('start_date')
            end_date = trigger_kwargs.get('end_date')
            if end_date:
                trigger_kwargs.pop('end_date')

            if not trigger_kwargs:
                start_date_2_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                trigger_kwargs['year'] = start_date_2_date.year
                trigger_kwargs['month'] = start_date_2_date.month
                trigger_kwargs['day'] = start_date_2_date.day
                trigger_kwargs['hour'] = start_date_2_date.hour
                trigger_kwargs['minute'] = start_date_2_date.minute
                trigger_kwargs['second'] = start_date_2_date.second
            trigger_kwargs['start_date'] = start_date
            if end_date:
                trigger_kwargs['end_date'] = end_date
            param['trigger_kwargs'] = trigger_kwargs

            # 先从Proxy获取是否存在，若不存在则新建
            api = APIRequest('{0}/v1.0/job/{1}'.format(task.task_proxy.url, task.task_uuid),
                             task.task_proxy.username,
                             CRYPTOR.decrypt(task.task_proxy.password))
            result, code = api.req_get()

            if code == 404:
                param['job_id'] = task.task_uuid
                param['task_name'] = task.task_type
                param['task_kwargs'] = json.loads(task.task_kwargs)
                # 任务已经完全结束，再次编辑时，proxy端需要重新创建
                api = APIRequest('{0}/v1.0/job'.format(task.task_proxy.url), task.task_proxy.username,
                                 CRYPTOR.decrypt(task.task_proxy.password))
                result, code = api.req_post(json.dumps(param))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    task.trigger_kwargs = json.dumps(trigger_kwargs)
                    task.comment = comment
                    task.is_get_last = '00'
                    task.task_statu = '00'
                    task.save()
            elif code == 200:
                api = APIRequest('{0}/v1.0/job/{1}'.format(task.task_proxy.url, task.task_uuid),
                                 task.task_proxy.username,
                                 CRYPTOR.decrypt(task.task_proxy.password))
                result, code = api.req_put(json.dumps(param))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    task.trigger_kwargs = json.dumps(trigger_kwargs)
                    task.comment = comment
                    task.save()
        except:
            logger.error(traceback.format_exc())
            res['flag'] = False
            res['content'] = "update error"
        else:
            res['flag'] = True
        return HttpResponse(json.dumps(res))
    elif request.method == "GET":
        task_id = request.GET.get('task_id')
        task = Task.objects.get(id=task_id).to_dict()
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        task['module'] = task['module'].to_dict()
        task['task_proxy'] = task['task_proxy'].to_dict()
        res['task'] = task
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
            # 先从Proxy获取是否存在，若不存在则新建
            api = APIRequest('{0}/v1.0/job/{1}'.format(task.task_proxy.url, task.task_uuid),
                             task.task_proxy.username,
                             CRYPTOR.decrypt(task.task_proxy.password))
            result, code = api.req_get()

            # 构建参数
            param = {'action': action}
            if code == 200:
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
            elif code == 404:
                logger.info("task [%s] have been deleted" % task.task_uuid)
                # 不存在时，若启用则创建，若禁用则直接修改为禁用
                if action == 'pause':
                    # 停用，直接修改为禁用
                    task.task_statu = '01'
                    task.save()
                elif action == 'resume':
                    res['flag'] = False
                    res['content'] = '触发器已过期，请使用编辑功能编辑触发器'
                    return HttpResponse(json.dumps(res))
        except ServerError, e:
            logger.error("action error %s" % str(e))
            error = e.message
            res['flag'] = False
            res['content'] = error
        except Exception, e:
            logger.error("error %s" % str(e))
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
            task_id = request.GET.get('task_id', None)
            job_id = request.GET.get('job_id', None)
            job = Task.objects.filter(task_uuid=job_id).first()
            url = '{0}/v1.0/job_task_replay/{1}'.format(job.task_proxy.url, task_id)
            content = json.load(urllib2.urlopen(url)).get('content')
            return HttpResponse(content)
        except:
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


def task_filter(objs, request):
    """
        根据指定备份类型进行过滤，结合前台的各字段含义进行解析
    """
    # 公共部分
    sSerach = request.POST.get('sSearch', '').strip()
    # 1. 查找可过滤内容， 如果没有过滤内容直接返回
    if not sSerach:
        return objs

    # 2. 查找出可使用过滤列，并根据列找出数据库对应 bSearchable_x
    pattern = re.compile(r'bSearchable_\d+')
    columns = filter(lambda x: pattern.match(x), list(request.POST))
    search_columns = []

    for col in columns:
        if request.POST.get(col):
            search_columns.append(col)

    if not search_columns:
        return objs

    # todo 过滤
    return objs


def task_order(objs, request):
    """
        根据指定备份类型，进行排序，需要结合前台的各字段含义进行解析
    """
    # todo 统一按照id倒叙排序
    return objs.order_by('-id')


def get_task_list(request, task_type=[]):
    """
        公共函数
        获取任务列表
        1. 前端通过jquery插件datatables填充数据表数据
        2. 后端根据备份类型，进行分页操作
    """
    # 初始化datatables要求结果格式
    return_obj = {
        "sEcho": request.POST.get('sEcho', 0), # 前端上传原样返回
        "iTotalRecords": 0, # 总记录数
        "iTotalDisplayRecords": 0, # 过滤后总记录数，暂时不知具体用法
        # 返回前端数据，内容可以为列表，也可以为字典，字典的话，必须要在前端指定mData，此处要和前端设置的一直
        "aaData": []
    }
    try:
        # 初始化数据
        objs = Task.objects.filter(task_type__in=task_type).exclude(task_statu='02')
        return_obj['iTotalRecords'] = return_obj['iTotalDisplayRecords'] = objs.count()
        # 获取前端上传数据，分页类，查询排序类
        # 1. 过滤类
        objs = task_filter(objs, request)
        return_obj['iTotalDisplayRecords'] = objs.count()
        # 2. 排序类
        objs = task_order(objs, request)
        # 3. 分页类
        # 前端datatable上传每页显示数据
        limit = int(request.POST.get('iDisplayLength', 0))
        # 前端datatable上送从第几条开始展示
        offset = int(request.POST.get('iDisplayStart', 5))
        # 非选择全部时，有过滤
        if limit > -1:
            objs = objs[offset:offset + limit]
            # 组织数据库查询数据
        for obj in objs:
            return_obj["aaData"].append({
                'proxy': obj.task_proxy.id,
                'proxy_name': obj.task_proxy.proxy_name,
                'b_trigger': obj.trigger_kwargs,
                'status': obj.task_statu,
                'task_type': dict(Task.TYPES).get(obj.task_type),
                'last_exec_time': obj.last_exec_time,
                'comment': obj.comment,
                'id': obj.id
            })
    except:
        logger.error(traceback.format_exc())
    return return_obj


@require_role('admin')
def adv_task_list(request):
    """
        查看数据库备份
    """
    if request.method == 'GET':
        # 第一次请求，到达首页
        return my_render('taskManage/adv/list.html', locals(), request)

    elif request.method == 'POST':
        # 返回数据
        return HttpResponse(json.dumps(get_task_list(request, ['ansible-pb', 'shell'])))

    else:
        pass


@require_role('admin')
@user_operator_record
def adv_task_add(request, res, *args):
    if request.method == 'POST':
        param = {}
        # 触发器
        trigger_kwargs = request.POST.get('trigger')
        task_name = request.POST.get('task_type')
        task_content = request.POST.get('task_content') # 文件内容
        task_host = request.POST.getlist('task_host[]') # 前端上送list时
        proxy = request.POST.get('proxy')
        comment = request.POST.get('comment')
        try:
            # 构建trigger
            init_trigger = trigger_kwargs = json.loads(trigger_kwargs)
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
            param['task_name'] = task_name
            task_kwargs = {}

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
                # 用于前端确定选择的asset
                tmp_d['id'] = host.id
                resource.append(tmp_d)
            task_kwargs['host_list'] = host_list
            task_kwargs['resource'] = resource
            task_kwargs['content'] = task_content
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
                            task_uuid=result['job']['job_id'], create_time=datetime.now())
                task.save()
        except ServerError, e:
            error = e.message
            res['flag'] = False
            res['content'] = error
        except Exception, e:
            logger.error(traceback.format_exc())
            res['flag'] = False
            res['content'] = e[1]
        else:
            res['flag'] = True
        return HttpResponse(json.dumps(res))
    elif request.method == "GET":
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        res['proxys'] = proxy_list
        res['task_types'] = Task.TYPES[1:]
        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def adv_task_edit(request, res, *args, **kwargs):
    if request.method == 'POST':
        param = {}
        # 触发器
        trigger_kwargs = request.POST.get('trigger')
        comment = request.POST.get('comment')
        task_id = int(request.POST.get('task_id'))
        try:
            task = Task.objects.get(id=task_id)
            # 构建trigger
            trigger_kwargs = json.loads(trigger_kwargs)
            start_date = trigger_kwargs.pop('start_date')
            end_date = trigger_kwargs.get('end_date')
            if end_date:
                trigger_kwargs.pop('end_date')

            if not trigger_kwargs:
                start_date_2_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                trigger_kwargs['year'] = start_date_2_date.year
                trigger_kwargs['month'] = start_date_2_date.month
                trigger_kwargs['day'] = start_date_2_date.day
                trigger_kwargs['hour'] = start_date_2_date.hour
                trigger_kwargs['minute'] = start_date_2_date.minute
                trigger_kwargs['second'] = start_date_2_date.second
            trigger_kwargs['start_date'] = start_date
            if end_date:
                trigger_kwargs['end_date'] = end_date
            param['trigger_kwargs'] = trigger_kwargs

            # 先从Proxy获取是否存在，若不存在则新建
            api = APIRequest('{0}/v1.0/job/{1}'.format(task.task_proxy.url, task.task_uuid),
                             task.task_proxy.username,
                             CRYPTOR.decrypt(task.task_proxy.password))
            result, code = api.req_get()

            if code == 404:
                param['job_id'] = task.task_uuid
                param['task_name'] = task.task_type
                param['task_kwargs'] = json.loads(task.task_kwargs)
                # 任务已经完全结束，再次编辑时，proxy端需要重新创建
                api = APIRequest('{0}/v1.0/job'.format(task.task_proxy.url), task.task_proxy.username,
                                 CRYPTOR.decrypt(task.task_proxy.password))
                result, code = api.req_post(json.dumps(param))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    task.trigger_kwargs = json.dumps(trigger_kwargs)
                    task.comment = comment
                    task.is_get_last = '00'
                    task.task_statu = '00'
                    task.save()
            elif code == 200:
                api = APIRequest('{0}/v1.0/job/{1}'.format(task.task_proxy.url, task.task_uuid),
                                 task.task_proxy.username,
                                 CRYPTOR.decrypt(task.task_proxy.password))
                result, code = api.req_put(json.dumps(param))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    task.trigger_kwargs = json.dumps(trigger_kwargs)
                    task.comment = comment
                    task.save()
        except:
            logger.error(traceback.format_exc())
            res['flag'] = False
            res['content'] = "update error"
        else:
            res['flag'] = True
        return HttpResponse(json.dumps(res))
    elif request.method == "GET":
        task_id = request.GET.get('task_id')
        task = Task.objects.get(id=task_id).to_dict()
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        task['task_proxy'] = task['task_proxy'].to_dict()
        res['task'] = task
        res['proxys'] = proxy_list
        res['task_types'] = Task.TYPES[1:]
        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def adv_task_action(request, res, *args, **kwargs):
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
def adv_task_del(request, res, *args, **kwargs):
    if request.method == 'POST':
        task_ids = request.POST.get('task_id')
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
def get_html_code(request):
    """
        根据给定代码，返回HTML代码
    """
    code = request.POST.get('code', '')
    _lexer = request.POST.get('lexer', 'yaml')
    _formatter = request.POST.get('formatter', 'html')
    res = {}
    res['r'] = code
    try:
        lexer = get_lexer_by_name(_lexer, stripall=True)
        formatter = get_formatter_by_name(_formatter)
        r = highlight(code, lexer, formatter)
        res['r'] = r
    except:
        logger.error(traceback.format_exc())
    return HttpResponse(json.dumps(res))
