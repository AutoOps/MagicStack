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
import traceback
import urllib2
import re
from django.db.models import Q
from django.shortcuts import render

from common.interface import APIRequest
from userManage.user_api import user_operator_record
from proxyManage.models import Proxy
from permManage.models import Asset
from MagicStack.api import *
from models import *
from datetime import datetime


@require_role('admin')
@user_operator_record
def dbbackup_add(request, res, *args):
    if request.method == 'POST':
        init_kwargs = dict()
        init_kwargs['db_user_name'] = db_user_name = request.POST.get('db_user_name')
        init_kwargs['db_password'] = db_password = request.POST.get('db_password')
        init_kwargs['db_host'] = db_host = request.POST.get('db_host')
        init_kwargs['db_port'] = db_port = request.POST.get('db_port', 3306)
        init_kwargs['db_backups'] = db_backups = request.POST.get('db_backups')
        init_kwargs['comment'] = comment = request.POST.get('comment')
        init_kwargs['ftp_user_name'] = ftp_user_name = request.POST.get('ftp_user_name')
        init_kwargs['ftp_password'] = ftp_password = request.POST.get('ftp_password')
        init_kwargs['ftp_host'] = ftp_host = request.POST.get('ftp_host')
        init_kwargs['ftp_port'] = ftp_port = request.POST.get('ftp_port', 21)
        init_kwargs['proxy'] = proxy = request.POST.get('proxy')
        init_kwargs['proxy_host'] = proxy_host = request.POST.get('proxy_host')
        init_kwargs['start_datetime'] = start_datetime = request.POST.get('start_datetime')
        init_kwargs['end_datetime'] = end_datetime = request.POST.get('end_datetime')
        init_kwargs['trigger_cycle'] = trigger_cycle = int(request.POST.get('trigger_cycle'))
        init_kwargs['cycle_val'] = cycle_val = request.POST.get('trigger_cycle')
        init_kwargs['cycle_type'] = cycle_type = int(request.POST.get('cycle_type'))
        init_kwargs['cycle_type_val'] = cycle_type_val = request.POST.getlist('cycle_type_val[]')
        init_kwargs['trigger_hour'] = trigger_hour = request.POST.get('trigger_hour')
        init_kwargs['trigger_minute'] = trigger_minute = request.POST.get('trigger_minute')
        init_kwargs['trigger_second'] = trigger_second = request.POST.get('trigger_second')
        init_kwargs['dest'] = dest = request.POST.get('dest')
        try:
            trigger_kwargs = {}

            start_date_2_date = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            # 构造触发器结构
            trigger_kwargs['start_date'] = start_datetime
            # 结束时间设置
            if end_datetime:
                trigger_kwargs['end_date'] = end_datetime

            if trigger_hour:
                trigger_kwargs['hour'] = trigger_hour
            else:
                trigger_kwargs['hour'] = start_date_2_date.hour

            if trigger_minute:
                trigger_kwargs['minute'] = trigger_minute
            else:
                trigger_kwargs['minute'] = start_date_2_date.minute

            # 前台不再展示秒级粒度，全部默认是0秒开始执行
            if trigger_second:
                trigger_kwargs['second'] = trigger_second
            else:
                trigger_kwargs['second'] = start_date_2_date.second

            if trigger_cycle == 1:
                # 一次性任务
                trigger_kwargs['year'] = start_date_2_date.year
                trigger_kwargs['month'] = start_date_2_date.month
                trigger_kwargs['day'] = start_date_2_date.day
            elif trigger_cycle == 2:
                # 每天
                trigger_kwargs['day'] = '*'
            elif trigger_cycle == 3:
                # 每星期x
                trigger_kwargs['day_of_week'] = int(cycle_val)
            elif trigger_cycle == 4:
                # 每月x号
                trigger_kwargs['day'] = int(cycle_val)
            else:
                # 自定义
                if len(cycle_type_val) > 1:
                    cycle_type_val = ','.join(cycle_type_val)
                else:
                    cycle_type_val = cycle_type_val[0]
                if cycle_type == 1:
                    # 按照星期定义
                    trigger_kwargs['day_of_week'] = cycle_type_val
                else:
                    # 按照月定义
                    trigger_kwargs['day'] = cycle_type_val

            # 构造ansible扩展模块backup数据
            backup_args = {
                'backup_type': 'database',
                # 备份信息
                'login_user': ftp_user_name,
                'login_password': ftp_password,
                'login_host': ftp_host,
                'login_port': ftp_port,
                # 数据库信息
                'db_login_host': db_host,
                'db_login_user': db_user_name,
                'db_login_password': db_password,
                'db_login_port': db_port,
                'name': db_backups,
                'dest': dest
            }
            module_args = " ".join(['{0}={1}'.format(k, v) for k, v in backup_args.items()])
            proxy_obj = Proxy.objects.get(id=proxy)
            asset_obj = Asset.objects.get(id=proxy_host)

            # 构造访问proxy数据
            task_kwargs = {
                'module_name': 'backup',
                'module_args': module_args,
                'host_list': [asset_obj.networking.all()[0].ip_address],
                'resource': [{
                                 "hostname": asset_obj.networking.all()[0].ip_address,
                                 "port": asset_obj.port,
                                 "username": asset_obj.username,
                                 "password": CRYPTOR.decrypt(asset_obj.password)
                             }]
            }

            params = {
                'task_name': 'ansible',
                'task_kwargs': task_kwargs,
                'trigger_kwargs': trigger_kwargs,
            }

            # 调用proxy接口，创建任务
            api = APIRequest('{0}/v1.0/job'.format(proxy_obj.url), proxy_obj.username,
                             CRYPTOR.decrypt(proxy_obj.password))
            result, code = api.req_post(json.dumps(params))
            if code != 200:
                raise ServerError(result['messege'])
            else:
            # 保存数据库
                dbbackup = Backup(proxy=proxy_obj, type='db', kwargs=json.dumps(params),
                                  b_trigger=json.dumps(trigger_kwargs), comment=comment,
                                  task_uuid=result['job']['job_id'], create_time=datetime.now(),
                                  ext1=json.dumps(init_kwargs))
                dbbackup.save()
            res['flag'] = True
        except:
            logger.error(traceback.format_exc())
            res['flag'] = False

        return HttpResponse(json.dumps(res))

    elif request.method == "GET":
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        res['proxys'] = proxy_list
        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def dbbackup_edit(request, res, *args):
    if request.method == 'GET':
        back_id = request.GET.get('backup_id')
        backup = Backup.objects.get(id=back_id).to_dict()
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        backup['proxy'] = backup['proxy'].to_dict()
        res['backup'] = backup
        res['proxys'] = proxy_list
        return HttpResponse(json.dumps(res))
    elif request.method == 'POST':
        try:
            back_id = request.POST.get('backup_id')
            backup = Backup.objects.get(id=back_id)
            init_kwargs = dict()
            init_kwargs['db_user_name'] = db_user_name = request.POST.get('db_user_name')
            init_kwargs['db_password'] = db_password = request.POST.get('db_password')
            init_kwargs['db_host'] = db_host = request.POST.get('db_host')
            init_kwargs['db_port'] = db_port = request.POST.get('db_port', 3306)
            init_kwargs['db_backups'] = db_backups = request.POST.get('db_backups')
            init_kwargs['comment'] = comment = request.POST.get('comment')
            init_kwargs['ftp_user_name'] = ftp_user_name = request.POST.get('ftp_user_name')
            init_kwargs['ftp_password'] = ftp_password = request.POST.get('ftp_password')
            init_kwargs['ftp_host'] = ftp_host = request.POST.get('ftp_host')
            init_kwargs['ftp_port'] = ftp_port = request.POST.get('ftp_port', 21)
            init_kwargs['proxy'] = proxy = request.POST.get('proxy')
            init_kwargs['proxy_host'] = proxy_host = request.POST.get('proxy_host')
            init_kwargs['start_datetime'] = start_datetime = request.POST.get('start_datetime')
            init_kwargs['end_datetime'] = end_datetime = request.POST.get('end_datetime')
            init_kwargs['trigger_cycle'] = trigger_cycle = int(request.POST.get('trigger_cycle'))
            init_kwargs['old_trigger_cycle'] = old_trigger_cycle = int(request.POST.get('old_trigger_cycle'))
            init_kwargs['cycle_val'] = cycle_val = request.POST.get('cycle_val')
            init_kwargs['old_cycle_val'] = old_cycle_val = request.POST.get('old_cycle_val')
            init_kwargs['cycle_type'] = cycle_type = int(request.POST.get('cycle_type'))
            init_kwargs['cycle_type_val'] = cycle_type_val = request.POST.getlist('cycle_type_val[]')
            init_kwargs['old_cycle_type_val'] = old_cycle_type_val = request.POST.get('old_cycle_type_val')
            init_kwargs['trigger_hour'] = trigger_hour = request.POST.get('trigger_hour')
            init_kwargs['trigger_minute'] = trigger_minute = request.POST.get('trigger_minute')
            init_kwargs['trigger_second'] = trigger_second = request.POST.get('trigger_second')
            init_kwargs['dest'] = dest = request.POST.get('dest')
            trigger_kwargs = {}

            start_date_2_date = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            # 构造触发器结构
            trigger_kwargs['start_date'] = start_datetime
            # 结束时间设置
            if end_datetime:
                trigger_kwargs['end_date'] = end_datetime

            if trigger_hour:
                trigger_kwargs['hour'] = trigger_hour
            else:
                trigger_kwargs['hour'] = start_date_2_date.hour

            if trigger_minute:
                trigger_kwargs['minute'] = trigger_minute
            else:
                trigger_kwargs['minute'] = start_date_2_date.minute

            # 前台不再展示秒级粒度，全部默认是0秒开始执行
            if trigger_second:
                trigger_kwargs['second'] = trigger_second
            else:
                trigger_kwargs['second'] = start_date_2_date.second

            if trigger_cycle == 1:
                # 一次性任务
                trigger_kwargs['year'] = start_date_2_date.year
                trigger_kwargs['month'] = start_date_2_date.month
                trigger_kwargs['day'] = start_date_2_date.day
            elif trigger_cycle == 2:
                # 每天
                trigger_kwargs['day'] = '*'
            elif trigger_cycle == 3:
                # 每星期x
                trigger_kwargs['day_of_week'] = int(cycle_val)
            elif trigger_cycle == 4:
                # 每月x号
                trigger_kwargs['day'] = int(cycle_val)
            elif trigger_cycle == 5:
                # 自定义
                if len(cycle_type_val) > 1:
                    cycle_type_val = ','.join(cycle_type_val)
                else:
                    cycle_type_val = cycle_type_val[0]
                if cycle_type == 1:
                    # 按照星期定义
                    trigger_kwargs['day_of_week'] = cycle_type_val
                else:
                    # 按照月定义
                    trigger_kwargs['day'] = cycle_type_val
            else:
                # 编辑时，还是保留原来的方式，特指 每周或每月
                if old_trigger_cycle == 3:
                    trigger_kwargs['day_of_week'] = int(old_cycle_val)
                else:
                    trigger_kwargs['day'] = int(old_cycle_val)

            # 构造ansible扩展模块backup数据
            backup_args = {
                'backup_type': 'database',
                # 备份信息
                'login_user': ftp_user_name,
                'login_password': ftp_password,
                'login_host': ftp_host,
                'login_port': ftp_port,
                # 数据库信息
                'db_login_host': db_host,
                'db_login_user': db_user_name,
                'db_login_password': db_password,
                'db_login_port': db_port,
                'name': db_backups,
                'dest': dest
            }
            module_args = " ".join(['{0}={1}'.format(k, v) for k, v in backup_args.items()])
            proxy_obj = Proxy.objects.get(id=proxy)
            asset_obj = Asset.objects.get(id=proxy_host)

            # 构造访问proxy数据
            task_kwargs = {
                'module_name': 'backup',
                'module_args': module_args,
                'host_list': [asset_obj.networking.all()[0].ip_address],
                'resource': [{
                                 "hostname": asset_obj.networking.all()[0].ip_address,
                                 "port": asset_obj.port,
                                 "username": asset_obj.username,
                                 "password": CRYPTOR.decrypt(asset_obj.password)
                             }]
            }

            params = {
                'task_name': 'ansible',
                'task_kwargs': task_kwargs,
                'trigger_kwargs': trigger_kwargs,
            }

            # 因为apscheduler接口不支持修改参数，所以需要先删除，创建
            # 调用proxy接口，
            api = APIRequest('{0}/v1.0/job/{1}'.format(backup.proxy.url, backup.task_uuid),
                             backup.proxy.username,
                             CRYPTOR.decrypt(backup.proxy.password))
            result, code = api.req_del(json.dumps({}))
            if code != 200:
                raise ServerError(result['messege'])
            else:
                params['job_id'] = backup.task_uuid
                api = APIRequest('{0}/v1.0/job'.format(backup.proxy.url), backup.proxy.username,
                                 CRYPTOR.decrypt(backup.proxy.password))
                result, code = api.req_post(json.dumps(params))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    backup.ext1 = json.dumps(init_kwargs)
                    backup.b_trigger = json.dumps(trigger_kwargs)
                    backup.kwargs = json.dumps(params)
                    backup.comment = comment
                    backup.is_get_last = '00'
                    backup.save()
            res['flag'] = True
        except:
            logger.error(traceback.format_exc())
            res['flag'] = False
        return HttpResponse(json.dumps(res))
    else:
        pass


@require_role('admin')
@user_operator_record
def dbbackup_del(request, res, *args):
    if request.method == 'POST':
        back_ids = request.POST.get('back_id')
        res['flag'] = True
        success = []
        fail = []
        # 循环删除
        for back_id in back_ids.split(','):
            back_up = Backup.objects.get(id=back_id)
            try:
                # 调用proxy接口，
                api = APIRequest('{0}/v1.0/job/{1}'.format(back_up.proxy.url, back_up.task_uuid),
                                 back_up.proxy.username,
                                 CRYPTOR.decrypt(back_up.proxy.password))
                result, code = api.req_del(json.dumps({}))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    back_up.status = '02'
                    back_up.save()
            except ServerError, e:
                fail.append(back_up)
                error = e.message
                res['flag'] = False
                res['content'] = error
            except Exception, e:
                fail.append(back_up)
                res['flag'] = False
                res['content'] = e[1]
            else:
                success.append(back_up)
        if len(success) + len(fail) > 1:
            res['content'] = 'success [%d] fail [%d]' % (len(success), len(fail))

        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def filebackup_add(request, res, *args):
    if request.method == 'POST':
        init_kwargs = dict()
        init_kwargs['comment'] = comment = request.POST.get('comment')
        init_kwargs['ftp_user_name'] = ftp_user_name = request.POST.get('ftp_user_name')
        init_kwargs['ftp_password'] = ftp_password = request.POST.get('ftp_password')
        init_kwargs['ftp_host'] = ftp_host = request.POST.get('ftp_host')
        init_kwargs['ftp_port'] = ftp_port = request.POST.get('ftp_port', 21)
        init_kwargs['proxy'] = proxy = request.POST.get('proxy')
        init_kwargs['proxy_host'] = proxy_host = request.POST.getlist('proxy_host[]')
        init_kwargs['start_datetime'] = start_datetime = request.POST.get('start_datetime')
        init_kwargs['end_datetime'] = end_datetime = request.POST.get('end_datetime')
        init_kwargs['trigger_cycle'] = trigger_cycle = int(request.POST.get('trigger_cycle'))
        init_kwargs['cycle_val'] = cycle_val = request.POST.get('trigger_cycle')
        init_kwargs['cycle_type'] = cycle_type = int(request.POST.get('cycle_type'))
        init_kwargs['cycle_type_val'] = cycle_type_val = request.POST.getlist('cycle_type_val[]')
        init_kwargs['trigger_hour'] = trigger_hour = request.POST.get('trigger_hour')
        init_kwargs['trigger_minute'] = trigger_minute = request.POST.get('trigger_minute')
        init_kwargs['trigger_second'] = trigger_second = request.POST.get('trigger_second')
        init_kwargs['dest'] = dest = request.POST.get('dest')
        init_kwargs['src'] = src = request.POST.get('src')

        try:
            trigger_kwargs = {}

            start_date_2_date = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            # 构造触发器结构
            trigger_kwargs['start_date'] = start_datetime
            # 结束时间设置
            if end_datetime:
                trigger_kwargs['end_date'] = end_datetime

            if trigger_hour:
                trigger_kwargs['hour'] = trigger_hour
            else:
                trigger_kwargs['hour'] = start_date_2_date.hour

            if trigger_minute:
                trigger_kwargs['minute'] = trigger_minute
            else:
                trigger_kwargs['minute'] = start_date_2_date.minute

            # 前台不再展示秒级粒度，全部默认是0秒开始执行
            if trigger_second:
                trigger_kwargs['second'] = trigger_second
            else:
                trigger_kwargs['second'] = start_date_2_date.second

            if trigger_cycle == 1:
                # 一次性任务
                trigger_kwargs['year'] = start_date_2_date.year
                trigger_kwargs['month'] = start_date_2_date.month
                trigger_kwargs['day'] = start_date_2_date.day
            elif trigger_cycle == 2:
                # 每天
                trigger_kwargs['day'] = '*'
            elif trigger_cycle == 3:
                # 每星期x
                trigger_kwargs['day_of_week'] = int(cycle_val)
            elif trigger_cycle == 4:
                # 每月x号
                trigger_kwargs['day'] = int(cycle_val)
            else:
                # 自定义
                if len(cycle_type_val) > 1:
                    cycle_type_val = ','.join(cycle_type_val)
                else:
                    cycle_type_val = cycle_type_val[0]
                if cycle_type == 1:
                    # 按照星期定义
                    trigger_kwargs['day_of_week'] = cycle_type_val
                else:
                    # 按照月定义
                    trigger_kwargs['day'] = cycle_type_val

            # 构造ansible扩展模块backup数据
            backup_args = {
                'backup_type': 'file',
                # 备份信息
                'login_user': ftp_user_name,
                'login_password': ftp_password,
                'login_host': ftp_host,
                'login_port': ftp_port,
                'dest': dest,
                'src': src
            }
            module_args = " ".join(['{0}={1}'.format(k, v) for k, v in backup_args.items()])
            proxy_obj = Proxy.objects.get(id=proxy)

            hosts = []
            if not proxy_host:
                hosts = Asset.objects.all().filter(proxy=proxy_obj)
                if not hosts:
                    # 没有可执行主机
                    raise ServerError("no exec host")
            else:
                for host_id in proxy_host:
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

            # 构造访问proxy数据
            task_kwargs = {
                'module_name': 'backup',
                'module_args': module_args,
                'host_list': host_list,
                'resource': resource
            }

            params = {
                'task_name': 'ansible',
                'task_kwargs': task_kwargs,
                'trigger_kwargs': trigger_kwargs,
            }

            # 调用proxy接口，创建任务
            api = APIRequest('{0}/v1.0/job'.format(proxy_obj.url), proxy_obj.username,
                             CRYPTOR.decrypt(proxy_obj.password))
            result, code = api.req_post(json.dumps(params))
            if code != 200:
                raise ServerError(result['messege'])
            else:
            # 保存数据库
                filebackup = Backup(proxy=proxy_obj, type='file', kwargs=json.dumps(params),
                                    b_trigger=json.dumps(trigger_kwargs), comment=comment,
                                    task_uuid=result['job']['job_id'], create_time=datetime.now(),
                                    ext1=json.dumps(init_kwargs))
                filebackup.save()
            res['flag'] = True
        except:
            logger.error(traceback.format_exc())
            res['flag'] = False

        return HttpResponse(json.dumps(res))

    elif request.method == "GET":
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        res['proxys'] = proxy_list
        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def filebackup_edit(request, res, *args):
    if request.method == 'GET':
        back_id = request.GET.get('backup_id')
        backup = Backup.objects.get(id=back_id).to_dict()
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        backup['proxy'] = backup['proxy'].to_dict()
        res['backup'] = backup
        res['proxys'] = proxy_list
        return HttpResponse(json.dumps(res))
    elif request.method == 'POST':
        try:
            back_id = request.POST.get('backup_id')
            backup = Backup.objects.get(id=back_id)
            init_kwargs = dict()
            init_kwargs['comment'] = comment = request.POST.get('comment')
            init_kwargs['ftp_user_name'] = ftp_user_name = request.POST.get('ftp_user_name')
            init_kwargs['ftp_password'] = ftp_password = request.POST.get('ftp_password')
            init_kwargs['ftp_host'] = ftp_host = request.POST.get('ftp_host')
            init_kwargs['ftp_port'] = ftp_port = request.POST.get('ftp_port', 21)
            init_kwargs['proxy'] = proxy = request.POST.get('proxy')
            init_kwargs['proxy_host'] = proxy_host = request.POST.getlist('proxy_host[]')
            init_kwargs['start_datetime'] = start_datetime = request.POST.get('start_datetime')
            init_kwargs['end_datetime'] = end_datetime = request.POST.get('end_datetime')
            init_kwargs['trigger_cycle'] = trigger_cycle = int(request.POST.get('trigger_cycle'))
            init_kwargs['old_trigger_cycle'] = old_trigger_cycle = int(request.POST.get('old_trigger_cycle'))
            init_kwargs['cycle_val'] = cycle_val = request.POST.get('cycle_val')
            init_kwargs['old_cycle_val'] = old_cycle_val = request.POST.get('old_cycle_val')
            init_kwargs['cycle_type'] = cycle_type = int(request.POST.get('cycle_type'))
            init_kwargs['cycle_type_val'] = cycle_type_val = request.POST.getlist('cycle_type_val[]')
            init_kwargs['old_cycle_type_val'] = old_cycle_type_val = request.POST.get('old_cycle_type_val')
            init_kwargs['trigger_hour'] = trigger_hour = request.POST.get('trigger_hour')
            init_kwargs['trigger_minute'] = trigger_minute = request.POST.get('trigger_minute')
            init_kwargs['trigger_second'] = trigger_second = request.POST.get('trigger_second')
            init_kwargs['dest'] = dest = request.POST.get('dest')
            init_kwargs['src'] = src = request.POST.get('src')

            trigger_kwargs = {}

            start_date_2_date = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            # 构造触发器结构
            trigger_kwargs['start_date'] = start_datetime
            # 结束时间设置
            if end_datetime:
                trigger_kwargs['end_date'] = end_datetime

            if trigger_hour:
                trigger_kwargs['hour'] = trigger_hour
            else:
                trigger_kwargs['hour'] = start_date_2_date.hour

            if trigger_minute:
                trigger_kwargs['minute'] = trigger_minute
            else:
                trigger_kwargs['minute'] = start_date_2_date.minute

            # 前台不再展示秒级粒度，全部默认是0秒开始执行
            if trigger_second:
                trigger_kwargs['second'] = trigger_second
            else:
                trigger_kwargs['second'] = start_date_2_date.second

            if trigger_cycle == 1:
                # 一次性任务
                trigger_kwargs['year'] = start_date_2_date.year
                trigger_kwargs['month'] = start_date_2_date.month
                trigger_kwargs['day'] = start_date_2_date.day
            elif trigger_cycle == 2:
                # 每天
                trigger_kwargs['day'] = '*'
            elif trigger_cycle == 3:
                # 每星期x
                trigger_kwargs['day_of_week'] = int(cycle_val)
            elif trigger_cycle == 4:
                # 每月x号
                trigger_kwargs['day'] = int(cycle_val)
            elif trigger_cycle == 5:
                # 自定义
                if len(cycle_type_val) > 1:
                    cycle_type_val = ','.join(cycle_type_val)
                else:
                    cycle_type_val = cycle_type_val[0]
                if cycle_type == 1:
                    # 按照星期定义
                    trigger_kwargs['day_of_week'] = cycle_type_val
                else:
                    # 按照月定义
                    trigger_kwargs['day'] = cycle_type_val
            else:
                # 编辑时，还是保留原来的方式，特指 每周或每月
                if old_trigger_cycle == 3:
                    trigger_kwargs['day_of_week'] = int(old_cycle_val)
                else:
                    trigger_kwargs['day'] = int(old_cycle_val)

            # 构造ansible扩展模块backup数据
            backup_args = {
                'backup_type': 'file',
                # 备份信息
                'login_user': ftp_user_name,
                'login_password': ftp_password,
                'login_host': ftp_host,
                'login_port': ftp_port,
                'dest': dest,
                'src': src
            }
            module_args = " ".join(['{0}={1}'.format(k, v) for k, v in backup_args.items()])
            proxy_obj = Proxy.objects.get(id=proxy)

            hosts = []
            if not proxy_host:
                hosts = Asset.objects.all().filter(proxy=proxy_obj)
                if not hosts:
                    # 没有可执行主机
                    raise ServerError("no exec host")
            else:
                for host_id in proxy_host:
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

            # 构造访问proxy数据
            task_kwargs = {
                'module_name': 'backup',
                'module_args': module_args,
                'host_list': host_list,
                'resource': resource
            }

            params = {
                'task_name': 'ansible',
                'task_kwargs': task_kwargs,
                'trigger_kwargs': trigger_kwargs,
            }

            # 因为apscheduler接口不支持修改参数，所以需要先删除，创建
            # 调用proxy接口，
            api = APIRequest('{0}/v1.0/job/{1}'.format(backup.proxy.url, backup.task_uuid),
                             backup.proxy.username,
                             CRYPTOR.decrypt(backup.proxy.password))
            result, code = api.req_del(json.dumps({}))
            if code != 200:
                raise ServerError(result['messege'])
            else:
                params['job_id'] = backup.task_uuid
                api = APIRequest('{0}/v1.0/job'.format(backup.proxy.url), backup.proxy.username,
                                 CRYPTOR.decrypt(backup.proxy.password))
                result, code = api.req_post(json.dumps(params))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    backup.ext1 = json.dumps(init_kwargs)
                    backup.b_trigger = json.dumps(trigger_kwargs)
                    backup.kwargs = json.dumps(params)
                    backup.comment = comment
                    backup.is_get_last = '00'
                    backup.save()
            res['flag'] = True
        except:
            logger.error(traceback.format_exc())
            res['flag'] = False
        return HttpResponse(json.dumps(res))
    else:
        pass


@require_role('admin')
@user_operator_record
def filebackup_del(request, res, *args):
    if request.method == 'POST':
        back_ids = request.POST.get('back_id')
        res['flag'] = True
        success = []
        fail = []
        # 循环删除
        for back_id in back_ids.split(','):
            back_up = Backup.objects.get(id=back_id)
            try:
                # 调用proxy接口，
                api = APIRequest('{0}/v1.0/job/{1}'.format(back_up.proxy.url, back_up.task_uuid),
                                 back_up.proxy.username,
                                 CRYPTOR.decrypt(back_up.proxy.password))
                result, code = api.req_del(json.dumps({}))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    back_up.status = '02'
                    back_up.save()
            except ServerError, e:
                fail.append(back_up)
                error = e.message
                res['flag'] = False
                res['content'] = error
            except Exception, e:
                fail.append(back_up)
                res['flag'] = False
                res['content'] = e[1]
            else:
                success.append(back_up)
        if len(success) + len(fail) > 1:
            res['content'] = 'success [%d] fail [%d]' % (len(success), len(fail))

        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def pathbackup_add(request, res, *args):
    if request.method == 'POST':
        init_kwargs = dict()
        init_kwargs['comment'] = comment = request.POST.get('comment')
        init_kwargs['ftp_user_name'] = ftp_user_name = request.POST.get('ftp_user_name')
        init_kwargs['ftp_password'] = ftp_password = request.POST.get('ftp_password')
        init_kwargs['ftp_host'] = ftp_host = request.POST.get('ftp_host')
        init_kwargs['ftp_port'] = ftp_port = request.POST.get('ftp_port', 21)
        init_kwargs['proxy'] = proxy = request.POST.get('proxy')
        init_kwargs['proxy_host'] = proxy_host = request.POST.getlist('proxy_host[]')
        init_kwargs['start_datetime'] = start_datetime = request.POST.get('start_datetime')
        init_kwargs['end_datetime'] = end_datetime = request.POST.get('end_datetime')
        init_kwargs['trigger_cycle'] = trigger_cycle = int(request.POST.get('trigger_cycle'))
        init_kwargs['cycle_val'] = cycle_val = request.POST.get('trigger_cycle')
        init_kwargs['cycle_type'] = cycle_type = int(request.POST.get('cycle_type'))
        init_kwargs['cycle_type_val'] = cycle_type_val = request.POST.getlist('cycle_type_val[]')
        init_kwargs['trigger_hour'] = trigger_hour = request.POST.get('trigger_hour')
        init_kwargs['trigger_minute'] = trigger_minute = request.POST.get('trigger_minute')
        init_kwargs['trigger_second'] = trigger_second = request.POST.get('trigger_second')
        init_kwargs['dest'] = dest = request.POST.get('dest')
        init_kwargs['src'] = src = request.POST.get('src')

        try:
            trigger_kwargs = {}

            start_date_2_date = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            # 构造触发器结构
            trigger_kwargs['start_date'] = start_datetime
            # 结束时间设置
            if end_datetime:
                trigger_kwargs['end_date'] = end_datetime

            if trigger_hour:
                trigger_kwargs['hour'] = trigger_hour
            else:
                trigger_kwargs['hour'] = start_date_2_date.hour

            if trigger_minute:
                trigger_kwargs['minute'] = trigger_minute
            else:
                trigger_kwargs['minute'] = start_date_2_date.minute

            # 前台不再展示秒级粒度，全部默认是0秒开始执行
            if trigger_second:
                trigger_kwargs['second'] = trigger_second
            else:
                trigger_kwargs['second'] = start_date_2_date.second

            if trigger_cycle == 1:
                # 一次性任务
                trigger_kwargs['year'] = start_date_2_date.year
                trigger_kwargs['month'] = start_date_2_date.month
                trigger_kwargs['day'] = start_date_2_date.day
            elif trigger_cycle == 2:
                # 每天
                trigger_kwargs['day'] = '*'
            elif trigger_cycle == 3:
                # 每星期x
                trigger_kwargs['day_of_week'] = int(cycle_val)
            elif trigger_cycle == 4:
                # 每月x号
                trigger_kwargs['day'] = int(cycle_val)
            else:
                # 自定义
                if len(cycle_type_val) > 1:
                    cycle_type_val = ','.join(cycle_type_val)
                else:
                    cycle_type_val = cycle_type_val[0]
                if cycle_type == 1:
                    # 按照星期定义
                    trigger_kwargs['day_of_week'] = cycle_type_val
                else:
                    # 按照月定义
                    trigger_kwargs['day'] = cycle_type_val

            # 构造ansible扩展模块backup数据
            backup_args = {
                'backup_type': 'path',
                # 备份信息
                'login_user': ftp_user_name,
                'login_password': ftp_password,
                'login_host': ftp_host,
                'login_port': ftp_port,
                'dest': dest,
                'src': src
            }
            module_args = " ".join(['{0}={1}'.format(k, v) for k, v in backup_args.items()])
            proxy_obj = Proxy.objects.get(id=proxy)

            hosts = []
            if not proxy_host:
                hosts = Asset.objects.all().filter(proxy=proxy_obj)
                if not hosts:
                    # 没有可执行主机
                    raise ServerError("no exec host")
            else:
                for host_id in proxy_host:
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

            # 构造访问proxy数据
            task_kwargs = {
                'module_name': 'backup',
                'module_args': module_args,
                'host_list': host_list,
                'resource': resource
            }

            params = {
                'task_name': 'ansible',
                'task_kwargs': task_kwargs,
                'trigger_kwargs': trigger_kwargs,
            }

            # 调用proxy接口，创建任务
            api = APIRequest('{0}/v1.0/job'.format(proxy_obj.url), proxy_obj.username,
                             CRYPTOR.decrypt(proxy_obj.password))
            result, code = api.req_post(json.dumps(params))
            if code != 200:
                raise ServerError(result['messege'])
            else:
            # 保存数据库
                pathbackup = Backup(proxy=proxy_obj, type='path', kwargs=json.dumps(params),
                                    b_trigger=json.dumps(trigger_kwargs), comment=comment,
                                    task_uuid=result['job']['job_id'], create_time=datetime.now(),
                                    ext1=json.dumps(init_kwargs))
                pathbackup.save()
            res['flag'] = True
        except:
            logger.error(traceback.format_exc())
            res['flag'] = False

        return HttpResponse(json.dumps(res))

    elif request.method == "GET":
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        res['proxys'] = proxy_list
        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def pathbackup_edit(request, res, *args):
    if request.method == 'GET':
        back_id = request.GET.get('backup_id')
        backup = Backup.objects.get(id=back_id).to_dict()
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        backup['proxy'] = backup['proxy'].to_dict()
        res['backup'] = backup
        res['proxys'] = proxy_list
        return HttpResponse(json.dumps(res))
    elif request.method == 'POST':
        try:
            back_id = request.POST.get('backup_id')
            backup = Backup.objects.get(id=back_id)
            init_kwargs = dict()
            init_kwargs['comment'] = comment = request.POST.get('comment')
            init_kwargs['ftp_user_name'] = ftp_user_name = request.POST.get('ftp_user_name')
            init_kwargs['ftp_password'] = ftp_password = request.POST.get('ftp_password')
            init_kwargs['ftp_host'] = ftp_host = request.POST.get('ftp_host')
            init_kwargs['ftp_port'] = ftp_port = request.POST.get('ftp_port', 21)
            init_kwargs['proxy'] = proxy = request.POST.get('proxy')
            init_kwargs['proxy_host'] = proxy_host = request.POST.getlist('proxy_host[]')
            init_kwargs['start_datetime'] = start_datetime = request.POST.get('start_datetime')
            init_kwargs['end_datetime'] = end_datetime = request.POST.get('end_datetime')
            init_kwargs['trigger_cycle'] = trigger_cycle = int(request.POST.get('trigger_cycle'))
            init_kwargs['old_trigger_cycle'] = old_trigger_cycle = int(request.POST.get('old_trigger_cycle'))
            init_kwargs['cycle_val'] = cycle_val = request.POST.get('cycle_val')
            init_kwargs['old_cycle_val'] = old_cycle_val = request.POST.get('old_cycle_val')
            init_kwargs['cycle_type'] = cycle_type = int(request.POST.get('cycle_type'))
            init_kwargs['cycle_type_val'] = cycle_type_val = request.POST.getlist('cycle_type_val[]')
            init_kwargs['old_cycle_type_val'] = old_cycle_type_val = request.POST.get('old_cycle_type_val')
            init_kwargs['trigger_hour'] = trigger_hour = request.POST.get('trigger_hour')
            init_kwargs['trigger_minute'] = trigger_minute = request.POST.get('trigger_minute')
            init_kwargs['trigger_second'] = trigger_second = request.POST.get('trigger_second')
            init_kwargs['dest'] = dest = request.POST.get('dest')
            init_kwargs['src'] = src = request.POST.get('src')

            trigger_kwargs = {}

            start_date_2_date = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            # 构造触发器结构
            trigger_kwargs['start_date'] = start_datetime
            # 结束时间设置
            if end_datetime:
                trigger_kwargs['end_date'] = end_datetime

            if trigger_hour:
                trigger_kwargs['hour'] = trigger_hour
            else:
                trigger_kwargs['hour'] = start_date_2_date.hour

            if trigger_minute:
                trigger_kwargs['minute'] = trigger_minute
            else:
                trigger_kwargs['minute'] = start_date_2_date.minute

            # 前台不再展示秒级粒度，全部默认是0秒开始执行
            if trigger_second:
                trigger_kwargs['second'] = trigger_second
            else:
                trigger_kwargs['second'] = start_date_2_date.second

            if trigger_cycle == 1:
                # 一次性任务
                trigger_kwargs['year'] = start_date_2_date.year
                trigger_kwargs['month'] = start_date_2_date.month
                trigger_kwargs['day'] = start_date_2_date.day
            elif trigger_cycle == 2:
                # 每天
                trigger_kwargs['day'] = '*'
            elif trigger_cycle == 3:
                # 每星期x
                trigger_kwargs['day_of_week'] = int(cycle_val)
            elif trigger_cycle == 4:
                # 每月x号
                trigger_kwargs['day'] = int(cycle_val)
            elif trigger_cycle == 5:
                # 自定义
                if len(cycle_type_val) > 1:
                    cycle_type_val = ','.join(cycle_type_val)
                else:
                    cycle_type_val = cycle_type_val[0]
                if cycle_type == 1:
                    # 按照星期定义
                    trigger_kwargs['day_of_week'] = cycle_type_val
                else:
                    # 按照月定义
                    trigger_kwargs['day'] = cycle_type_val
            else:
                # 编辑时，还是保留原来的方式，特指 每周或每月
                if old_trigger_cycle == 3:
                    trigger_kwargs['day_of_week'] = int(old_cycle_val)
                else:
                    trigger_kwargs['day'] = int(old_cycle_val)

            # 构造ansible扩展模块backup数据
            backup_args = {
                'backup_type': 'file',
                # 备份信息
                'login_user': ftp_user_name,
                'login_password': ftp_password,
                'login_host': ftp_host,
                'login_port': ftp_port,
                'dest': dest,
                'src': src
            }
            module_args = " ".join(['{0}={1}'.format(k, v) for k, v in backup_args.items()])
            proxy_obj = Proxy.objects.get(id=proxy)

            hosts = []
            if not proxy_host:
                hosts = Asset.objects.all().filter(proxy=proxy_obj)
                if not hosts:
                    # 没有可执行主机
                    raise ServerError("no exec host")
            else:
                for host_id in proxy_host:
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

            # 构造访问proxy数据
            task_kwargs = {
                'module_name': 'backup',
                'module_args': module_args,
                'host_list': host_list,
                'resource': resource
            }

            params = {
                'task_name': 'ansible',
                'task_kwargs': task_kwargs,
                'trigger_kwargs': trigger_kwargs,
            }

            # 因为apscheduler接口不支持修改参数，所以需要先删除，创建
            # 调用proxy接口，
            api = APIRequest('{0}/v1.0/job/{1}'.format(backup.proxy.url, backup.task_uuid),
                             backup.proxy.username,
                             CRYPTOR.decrypt(backup.proxy.password))
            result, code = api.req_del(json.dumps({}))
            if code != 200:
                raise ServerError(result['messege'])
            else:
                params['job_id'] = backup.task_uuid
                api = APIRequest('{0}/v1.0/job'.format(backup.proxy.url), backup.proxy.username,
                                 CRYPTOR.decrypt(backup.proxy.password))
                result, code = api.req_post(json.dumps(params))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    backup.ext1 = json.dumps(init_kwargs)
                    backup.b_trigger = json.dumps(trigger_kwargs)
                    backup.kwargs = json.dumps(params)
                    backup.comment = comment
                    backup.is_get_last = '00'
                    backup.save()
            res['flag'] = True
        except:
            logger.error(traceback.format_exc())
            res['flag'] = False
        return HttpResponse(json.dumps(res))
    else:
        pass


@require_role('admin')
@user_operator_record
def pathbackup_del(request, res, *args):
    if request.method == 'POST':
        back_ids = request.POST.get('back_id')
        res['flag'] = True
        success = []
        fail = []
        # 循环删除
        for back_id in back_ids.split(','):
            back_up = Backup.objects.get(id=back_id)
            try:
                # 调用proxy接口，
                api = APIRequest('{0}/v1.0/job/{1}'.format(back_up.proxy.url, back_up.task_uuid),
                                 back_up.proxy.username,
                                 CRYPTOR.decrypt(back_up.proxy.password))
                result, code = api.req_del(json.dumps({}))
                if code != 200:
                    raise ServerError(result['messege'])
                else:
                    back_up.status = '02'
                    back_up.save()
            except ServerError, e:
                fail.append(back_up)
                error = e.message
                res['flag'] = False
                res['content'] = error
            except Exception, e:
                fail.append(back_up)
                res['flag'] = False
                res['content'] = e[1]
            else:
                success.append(back_up)
        if len(success) + len(fail) > 1:
            res['content'] = 'success [%d] fail [%d]' % (len(success), len(fail))

        return HttpResponse(json.dumps(res))


def backup_filter(objs, backup_type, request):
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

    # 各类型分类
    if backup_type == 'db':
        # 数据库备份
        # todo 对于proxy这种过滤的需要再次测试，目前以全部like方式获取
        return objs.filter(comment__contains=sSerach)

    elif backup_type == 'file':
        # 文件备份
        return objs.filter(comment__contains=sSerach)
    elif backup_type == 'path':
        return objs.filter(comment__contains=sSerach)
    else:
        return objs


def backup_order(objs, backup_type, request):
    """
        根据指定备份类型，进行排序，需要结合前台的各字段含义进行解析
    """
    # 1. 查看是否有；排序的列
    iSortingCols = int(request.POST.get('iSortingCols', 0))
    if not iSortingCols:
        return objs

    # 2. 查看是否有可用的排序列
    pattern = re.compile(r'bSortable_\d+') # 可排序列
    columns = filter(lambda x: pattern.match(x), list(request.POST))
    sort_columns = []

    for col in columns:
        if request.POST.get(col):
            sort_columns.append(col)

    if not sort_columns:
        return objs

    # 3. 根据不同备份类型，前台对应排序列有所区别
    if backup_type == 'db':

        for idx in range(0, iSortingCols):
            # 得到排序列索引
            sort_idx = request.POST.get('iSortCol_{0}'.format(idx))
            # 得到排序方向
            fx = request.POST.get('sSortDir_{0}'.format(idx))
            # 得到排序列名字
            cname = request.POST.get('mDataProp_{0}'.format(sort_idx))
            if fx == 'desc':
                objs = objs.order_by('-{0}'.format(cname))
            else:
                objs = objs.order_by(cname)
    elif backup_type == 'file':
        pass
    elif backup_type == 'path':
        pass

    return objs


def get_backup_list(request, backup_type='db'):
    """
        公共函数
        获取备份列表
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
        objs = Backup.objects.filter(type=backup_type)
        return_obj['iTotalRecords'] = return_obj['iTotalDisplayRecords'] = objs.count()
        # 获取前端上传数据，分页类，查询排序类
        # 1. 过滤类
        objs = backup_filter(objs, backup_type, request)
        return_obj['iTotalDisplayRecords'] = objs.count()
        # 2. 排序类
        objs = backup_order(objs, backup_type, request)
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
                'proxy': obj.proxy.id,
                'proxy_name': obj.proxy.proxy_name,
                'b_trigger': obj.b_trigger,
                'status': obj.status,
                'last_exec_time': obj.last_exec_time,
                'comment': obj.comment,
                'id': obj.id
            })
    except:
        logger.error(traceback.format_exc())
    return return_obj


@require_role('admin')
def dbbackup_list(request):
    """
        查看数据库备份
    """
    if request.method == 'GET':
        # 第一次请求，到达首页
        return my_render('backupManage/dbback/list.html', locals(), request)

    elif request.method == 'POST':
        # 返回数据
        return HttpResponse(json.dumps(get_backup_list(request)))

    else:
        pass


@require_role('admin')
def filebackup_list(request):
    """
        查看文件备份
    """
    if request.method == 'GET':
        # 第一次请求，到达首页
        return my_render('backupManage/fileback/list.html', locals(), request)

    elif request.method == 'POST':
        # 返回数据
        return HttpResponse(json.dumps(get_backup_list(request, backup_type='file')))
    else:
        pass


@require_role('admin')
def pathbackup_list(request):
    """
        查看目录备份
    """
    if request.method == 'GET':
        # 第一次请求，到达首页
        return my_render('backupManage/pathback/list.html', locals(), request)

    elif request.method == 'POST':
        # 返回数据
        return HttpResponse(json.dumps(get_backup_list(request, backup_type='path')))

    else:
        pass


@require_role('admin')
def backup_exec_info(request):
    """
        获取备份执行信息
        前端使用jquery plugin datatables进行分页
        后端根据前端规则组合数据
    """
    res = {}
    if request.method == 'POST':
        # 初始化返回结果
        return_obj = {
            "sEcho": request.POST.get('sEcho', 0), # 前端上传原样返回
            "iTotalRecords": 0, # 总记录数
            "iTotalDisplayRecords": 0, # 过滤后总记录数
            "aaData": [] # 返回前端数据，json格式
        }

        # 获取过滤条件
        backup_id = request.POST.get('backup_id')
        # 前端datatable上传每页显示数据
        limit = request.POST.get('iDisplayLength', 0)
        # 前端datatable上送从第几条开始展示
        offset = request.POST.get('iDisplayStart', 5)
        backup = Backup.objects.get(id=backup_id)

        # 获取数据
        try:
            # 调用proxy接口，
            api = APIRequest(
                '{0}/v1.0/job_task/{1}?limit={2}&offset={3}'.format(backup.proxy.url, backup.task_uuid, limit, offset),
                backup.proxy.username,
                CRYPTOR.decrypt(backup.proxy.password))
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
            logger.error("GET BACKUP TAST EXEC INFO ERROR\n {0}".format(traceback.format_exc()))

        return HttpResponse(json.dumps(return_obj))


@require_role('admin')
def backup_exec_replay(request):
    """
        backup task 回放
    """
    if request.method == "POST":
        try:
            backup_id = request.GET.get('backup_id', None)
            job_id = request.GET.get('job_id', None)
            job = Backup.objects.filter(task_uuid=job_id).first()
            url = '{0}/v1.0/job_task_replay/{1}'.format(job.proxy.url, backup_id)
            content = json.load(urllib2.urlopen(url)).get('content')
            return HttpResponse(content)
        except:
            logger.error(traceback.format_exc())
            return HttpResponse({})
    elif request.method == 'GET':
        return render(request, 'logManage/record.html')

    else:
        return HttpResponse("ERROR METHOD!")


def read_file(filename, buf_size=8192):
    with open(filename, "rb") as f:
        while True:
            content = f.read(buf_size)
            if content:
                yield content
            else:
                break


def backup_download(request):
    logger.info(">>>>>>>>>>>>>>>>>>>")
    filename = "/var/MagicStack/MagicStack/t2cloud.zip"
    response = HttpResponse(read_file(filename))
    return response


