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

import uuid
import os
import traceback

from MagicStack.settings import UPLOAD_DIR, DOWNLOAD_DIR
from MagicStack.api import *
from proxyManage.models import Proxy
from assetManage.models import Asset
from common.interface import APIRequest
from utils import API
from models import File


@require_role('admin')
def upload(request):
    if request.method == 'POST':
        # 上传到本地目录
        try:
            path = request.POST.get('path')
            proxy = request.POST.get('proxy')
            proxy_host = request.POST.getlist('proxy_host')
            # 上传到本地
            f = request.FILES['file']
            df = handle_uploaded_file(f)
            files = {'file': (f.name, open(df, 'rb'))}
            params = {'action': 'upload'}
            # 通过proxy处理文件
            proxy_obj = Proxy.objects.get(id=proxy)
            tnow = datetime.datetime.now()

            # 调用proxy接口，上传文件
            api = API('{0}/v1.0/upload'.format(proxy_obj.url), proxy_obj.username,
                      CRYPTOR.decrypt(proxy_obj.password))

            result, code = api.req_post(data=params, files=files)
            if code != 200:
                file = File(path=path, proxy=proxy_obj, create_time=tnow, status='01',
                            result="上传文件失败")
                file.save()
                raise ServerError(result['messege'])
                # 上传文件成功之后，调用proxy接口，进行文件上传任务
            hosts = []
            if not proxy_host:
                hosts = Asset.objects.all().filter(proxy=proxy_obj)
                if not hosts:
                    # 没有可执行主机
                    file = File(path=path, proxy=proxy_obj, create_time=tnow, status='01',
                                result="没有可执行主机")
                    file.save()
                    raise RuntimeError("没有可执行主机")

            else:
                for host_id in proxy_host:
                    hosts.append(Asset.objects.get(id=host_id))

            host_list = []
            resource = []
            params = {}
            trigger_kwargs = {}
            trigger_kwargs['year'] = tnow.year
            trigger_kwargs['month'] = tnow.month
            trigger_kwargs['day'] = tnow.day
            trigger_kwargs['hour'] = tnow.hour
            trigger_kwargs['minute'] = tnow.minute
            trigger_kwargs['second'] = tnow.second
            params['trigger_kwargs'] = trigger_kwargs
            params['task_name'] = 'ansible'
            task_kwargs = {}
            task_kwargs['module_name'] = 'copy'
            task_kwargs['module_args'] = 'src={0} dest={1}'.format(result.get('fp'), path)

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
            params['task_kwargs'] = task_kwargs
            # 调用proxy接口，创建任务
            api = APIRequest('{0}/v1.0/job'.format(proxy_obj.url), proxy_obj.username,
                             CRYPTOR.decrypt(proxy_obj.password))
            result, code = api.req_post(json.dumps(params))
            if code != 200:
                file = File(path=path, proxy=proxy_obj, create_time=tnow,
                            status='01', result="上传文件失败")
                file.save()
            else:
                file = File(path=path, proxy=proxy_obj, task_uuid=result['job']['job_id'],
                            create_time=tnow)
                file.save()
        except Exception, e:
            logger.error(traceback.format_exc())
        return HttpResponseRedirect(reverse('file_upload'))

    else:
        once = request.GET.get('once', None)
        if once:
            # 获取proxy
            proxy_list = [proxy.to_dict() for proxy in Proxy.objects.all().order_by('create_time')]
            return HttpResponse(json.dumps(proxy_list))
        else:
            header_title, path1, path2 = u'文件上传', u'文件管理', u'文件上传'
            return render_to_response('fileManage/upload/index.html', locals())


def handle_uploaded_file(f):
    # 防止出现覆盖问题，所有的文件上传之时，全部添加uuid作为前缀
    newfilename = '%s.%s' % ( str(uuid.uuid1()), f.name)
    df = os.sep.join([UPLOAD_DIR, newfilename])
    with open(df, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return df


@require_role('admin')
def file_upload_list(request):
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
        objs = File.objects.all().order_by('-id')
        return_obj['iTotalRecords'] = return_obj['iTotalDisplayRecords'] = objs.count()

        # 获取前端上传数据，分页类，查询排序类
        # 1. 过滤类 todo
        # 2. 排序类 todo
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
                'create_time': obj.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'path': obj.path,
                'result': obj.result,
                'id': obj.id
            })
    except:
        logger.error(traceback.format_exc())
    return HttpResponse(json.dumps(return_obj))


@require_role('admin')
def download(request):
    if request.method == 'POST':
        # 上传到本地目录
        res = {'result': False}
        try:
            path = request.POST.get('path')
            proxy = request.POST.get('proxy')
            proxy_host = request.POST.get('proxy_host')
            params = {'action': 'download_ansible'}
            # 通过proxy处理文件
            proxy_obj = Proxy.objects.get(id=proxy)
            hosts = []
            if not proxy_host:
                raise RuntimeError("没有可执行主机")
            else:
                hosts.append(Asset.objects.get(id=int(proxy_host)))
            host_list = []
            resource = []
            params['path'] = path
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
            params['host_list'] = host_list
            params['resource'] = resource

            api = APIRequest(
                '{0}/v1.0/download'.format(proxy_obj.url), proxy_obj.username,
                CRYPTOR.decrypt(proxy_obj.password))
            result, code = api.req_post(json.dumps(params))
            if code != 200:
                res['message'] = result['message']
            else:
                res['result'] = True
                link = "{0}/v1.0/download?link_id={1}".format(proxy_obj.url, result['link'])
                res['link'] = link
                logger.info("link => {0}".format(res))
        except Exception, e:
            logger.info(traceback.format_exc())
            res['message'] = '失败'
        return HttpResponse(json.dumps(res))

    else:
        header_title, path1, path2 = u'文件下载', u'文件管理', u'文件下载'
        return render_to_response('fileManage/download/index.html', locals())
