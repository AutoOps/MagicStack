# -*- coding:utf-8 -*-
from django.db.models import Q
from MagicStack.api import *
from models import *
from userManage.user_api import user_operator_record
from datetime import datetime

@require_role('admin')
def proxy_list(request):
    """
    查看proxy
    """
    header_title, path1, path2 = '查看代理', '代理管理', '查看代理'
    keyword = request.GET.get('search', '')
    proxy_lists = Proxy.objects.all().order_by('create_time')
    proxy_id = request.GET.get('id', '')

    if keyword:
        proxy_lists = proxy_lists.filter(Q(name__icontains=keyword) | Q(create_time__icontains=keyword))

    if proxy_id:
        proxy_lists = proxy_lists.filter(id=int(proxy_id))

    proxy_lists, p, proxys, page_range, current_page, show_first, show_end = pages(proxy_lists, request)
    return my_render('proxyManage/proxy_list.html', locals(), request)


@require_role('admin')
@user_operator_record
def proxy_add(request, res, *args):
    error = msg = ''
    header_title, path1, path2 = '添加代理', '代理管理', '添加代理'
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
                raise ServerError('Proxy名不能为空')
            if Proxy.objects.filter(proxy_name=proxy_name):
                raise ServerError('Proxy名已存在')

        except ServerError, e:
            error = e
            res['flag'] = False
            res['content'] = error
        else:

            create_time = datetime.now()
            Proxy.objects.create(proxy_name=proxy_name, username=user_name, password=encrypt,
                                 url=proxy_url, comment=comment, create_time=create_time)
            msg = '添加Proxy[%s]成功' % proxy_name
            res['content'] = msg
            return HttpResponseRedirect(reverse('proxy_list'))

    return my_render('proxyManage/proxy_add.html', locals(), request)


@require_role('admin')
@user_operator_record
def proxy_edit(request, res, *args):
    error = msg = ''
    header_title, path1, path2 = '编辑代理', '代理管理', '编辑代理'
    res['operator'] = path2
    id = request.GET.get('id', '')
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
                raise ServerError('Proxy名不能为空')

            if proxy.proxy_name != proxy_name and Proxy.objects.filter(proxy_name=proxy_name):
                raise ServerError('Proxy名已存在')

        except ServerError, e:
            error = e
            res['flag'] = 'false'
            res['content'] = e
        else:
            proxy.proxy_name = proxy_name
            proxy.username = user_name
            proxy.password = encrypt
            proxy.url = proxy_url
            proxy.comment = comment
            proxy.save()
            msg = u'编辑Proxy[%s]成功' % proxy_name
            res['content'] = msg
            return HttpResponseRedirect(reverse('proxy_list'))
    return my_render('proxyManage/proxy_edit.html', locals(), request)


@require_role('admin')
@user_operator_record
def proxy_del(request, res, *args):
    msg = ''
    res['operator'] = '删除代理'
    res['content'] = '删除代理'
    proxy_id = request.GET.get('id')
    id_list = proxy_id.split(',')
    for pid in id_list:
        proxy = get_object(Proxy, id=int(pid))
        msg += '  %s  ' % proxy.proxy_name
        res['content'] += ' [%s]  ' % proxy.proxy_name
        proxy.delete()
    return HttpResponse('删除[%s]成功' % msg)
