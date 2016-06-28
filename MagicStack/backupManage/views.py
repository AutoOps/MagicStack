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
from django.db.models import Q

from userManage.user_api import user_operator_record
from proxyManage.models import Proxy
from MagicStack.api import *
from models import *
from datetime import datetime


@require_role('admin')
@user_operator_record
def dbbackup_add(request, res, *args):
    if request.method == 'POST':
        pass
    elif request.method == "GET":
        proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
        res['proxys'] = proxy_list
        logger.info(">>>>>>>>>> {0}".format(res))
        return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def dbbackup_edit(request, res, *args):
    pass


@require_role('admin')
def filebackup_list(request):
    """
        查看文件备份
    """
    pass


@require_role('admin')
def pathbackup_list(request):
    """
        查看目录备份
    """
    pass


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
        return objs.filter(Q(proxy__contains=sSerach) | Q(comment__contains=sSerach))

    elif backup_type == 'file':
        # 文件备份
        pass
    elif backup_type == 'path':
        pass
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

    try:
        # 组织数据库查询数据
        for obj in objs:
            return_obj["aaData"].append(obj.to_dict())
    except:
        import traceback

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