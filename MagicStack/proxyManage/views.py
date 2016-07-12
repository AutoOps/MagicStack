# -*- coding:utf-8 -*-
from django.db.models import Q
from MagicStack.api import *
from models import *
from userManage.user_api import user_operator_record
from assetManage.models import Asset
from datetime import datetime
import json


@require_role('admin')
def proxy_list(request):
    """
    查看proxy
    """
    if request.method == "GET":
        header_title, path1, path2 = u'查看代理', u'代理管理', u'查看代理'
        proxy_lists = Proxy.objects.all()
        return my_render('proxyManage/proxy_list.html',locals(),request)
    else:
        page_length = int(request.POST.get('length', '5'))
        total_length = Proxy.objects.all().count()
        keyword = request.POST.get("search")
        rest = {
            "iTotalRecords": page_length,   # 本次加载记录数量
            "iTotalDisplayRecords": total_length,  # 总记录数量
            "aaData": []}
        page_start = int(request.POST.get('start', '0'))
        page_end = page_start + page_length
        page_data = Proxy.objects.all()[page_start:page_end]
        data = []
        for item in page_data:
            res = {}
            res['id'] = item.id
            res['name'] = item.proxy_name
            res['asset'] = item.asset_set.all().count()
            res['username'] = item.username
            res['url'] = item.url
            res['comment'] = item.comment
            data.append(res)
        rest['aaData'] = data
        return HttpResponse(json.dumps(rest), content_type='application/json')



@require_role('admin')
@user_operator_record
def proxy_add(request, res, *args):
    error = msg = ''
    header_title, path1, path2 = u'添加代理', u'代理管理', u'添加代理'
    res['operator'] = path2
    res['emer_content'] = 7
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
            res['emer_status'] = u"添加proxy[%s]失败:%s"%(proxy_name,error)
        else:
            create_time = datetime.now()
            Proxy.objects.create(proxy_name=proxy_name, username=user_name, password=encrypt,
                                 url=proxy_url, comment=comment, create_time=create_time)
            msg = u'添加Proxy[%s]成功' % proxy_name
            res['flag'] = True
            res['content'] = msg
            res['emer_status'] = msg
        return HttpResponse(json.dumps(res))

    return my_render('proxyManage/proxy_add.html', locals(), request)


@require_role('admin')
@user_operator_record
def proxy_edit(request, res, *args):
    header_title, path1, path2 = u'编辑代理', u'代理管理', u'编辑代理'
    res['operator'] = path2
    res['emer_content'] = 7
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
            res['emer_status'] = u"编辑proxy[%s]失败:%s"%(proxy.proxy_name, e.message)
        else:
            proxy.proxy_name = proxy_name
            proxy.username = user_name
            proxy.password = encrypt
            proxy.url = proxy_url
            proxy.comment = comment
            proxy.save()
            msg = u'编辑Proxy[%s]成功' % proxy_name
            res['content'] = msg
            res['emer_status'] = msg
        return HttpResponse(json.dumps(res))

    res['proxy_id'] = proxy.id
    res['proxy_name'] = proxy.proxy_name
    res['username'] = proxy.username
    res['password'] = CRYPTOR.decrypt(proxy.password)
    res['proxy_url'] = proxy.url
    res['comment'] = proxy.comment
    return HttpResponse(json.dumps(res))


@require_role('admin')
@user_operator_record
def proxy_del(request, res, *args):
    msg = ''
    res['operator'] = u'删除代理'
    res['content'] = u'删除代理'
    res['emer_content'] = 7
    proxy_id = request.POST.get('id')
    id_list = proxy_id.split(',')
    if id_list:
        for pid in id_list:
            proxy = get_object(Proxy, id=int(pid))
            res['content'] += ' [%s]  ' % proxy.proxy_name
            proxy.delete()
        msg = res['content'] + u"成功"
        res['emer_status'] = msg

    else:
        msg = u"删除代理失败:ID不存在"
        res['flag'] = 'false'
        res['content'] = msg
        res['emer_status'] = msg
    return HttpResponse(msg)


@require_role('admin')
def get_host_for_proxy(request):
    """
        根据proxyId，获取主机列表
    """

    proxy_id = request.POST.get('proxy_id')
    assets = Asset.objects.all().filter(proxy=Proxy.objects.get(id=proxy_id)).order_by('id')
    res = list()
    for asset in assets:
        res.append({
            'id': asset.id,
            'name': asset.name
        })
    return HttpResponse(json.dumps(res))