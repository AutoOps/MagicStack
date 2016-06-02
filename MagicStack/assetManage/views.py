# -*- coding:utf-8 -*-

from django.db.models import Q
from assetManage.asset_api import *
from MagicStack.api import *
from MagicStack.models import Setting
from assetManage.forms import AssetForm, IdcForm,NetWorkingForm,NetWorkingGlobalForm,PowerManageForm
from assetManage.models import *
from permManage.perm_api import get_group_asset_perm, get_group_user_perm
from userManage.user_api import user_operator_record
from common.interface import APIRequest
from common.models import Task
import Queue
import time

task_queue = Queue.Queue()

@require_role('admin')
@user_operator_record
def group_add(request, res,*args):
    """
    Group add view
    添加资产组
    """
    header_title, path1, path2 = u'添加资产组', u'资产管理', u'添加资产组'
    res['operator'] = path2
    asset_all = Asset.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '')
        asset_select = request.POST.getlist('asset_select', [])
        comment = request.POST.get('comment', '')

        try:
            if not name:
                emg = u'组名不能为空'
                raise ServerError(emg)

            asset_group_test = get_object(AssetGroup, name=name)
            if asset_group_test:
                emg = u"该组名 %s 已存在" % name
                raise ServerError(emg)

        except ServerError:
            res['flag'] = 'false'
            res['content'] = emg

        else:
            db_add_group(name=name, comment=comment, asset_select=asset_select)
            smg = u"主机组 %s 添加成功" % name
            res['content'] = smg

    return my_render('assetManage/group_add.html', locals(), request)


@require_role('admin')
@user_operator_record
def group_edit(request,res, *args):
    """
    Group edit view
    编辑资产组
    """
    header_title, path1, path2 = u'编辑主机组', u'资产管理', u'编辑主机组'
    res['operator'] = path2
    group_id = request.GET.get('id', '')
    group = get_object(AssetGroup, id=group_id)

    asset_all = Asset.objects.all()
    asset_select = Asset.objects.filter(group=group)
    asset_no_select = [a for a in asset_all if a not in asset_select]

    if request.method == 'POST':
        name = request.POST.get('name', '')
        asset_select = request.POST.getlist('asset_select', [])
        comment = request.POST.get('comment', '')

        try:
            if not name:
                emg = u'组名不能为空'
                raise ServerError(emg)

            if group.name != name:
                asset_group_test = get_object(AssetGroup, name=name)
                if asset_group_test:
                    emg = u"该组名 %s 已存在" % name
                    raise ServerError(emg)

        except ServerError:
            res['flag'] = 'false'
            res['content'] = emg

        else:
            group.asset_set.clear()
            db_update_group(id=group_id, name=name, comment=comment, asset_select=asset_select)
            smg = u"主机组 %s 添加成功" % name
            res['content'] = smg

        return HttpResponseRedirect(reverse('asset_group_list'))

    return my_render('assetManage/group_edit.html', locals(), request)


@require_role('admin')
def group_list(request):
    """
    list asset group
    列出资产组
    """
    header_title, path1, path2 = u'查看资产组', u'资产管理', u'查看资产组'
    keyword = request.GET.get('keyword', '')
    asset_group_list = AssetGroup.objects.all()
    group_id = request.GET.get('id')
    if group_id:
        asset_group_list = asset_group_list.filter(id=group_id)
    if keyword:
        asset_group_list = asset_group_list.filter(Q(name__contains=keyword) | Q(comment__contains=keyword))

    asset_group_list, p, asset_groups, page_range, current_page, show_first, show_end = pages(asset_group_list, request)
    return my_render('assetManage/group_list.html', locals(), request)


@require_role('admin')
@user_operator_record
def group_del(request,res, *args):
    """
    Group delete view
    删除主机组
    """
    res['operator'] = u'删除主机组'
    res['content'] = u'删除主机组'
    group_ids = request.GET.get('id', '')
    group_id_list = group_ids.split(',')
    for group_id in group_id_list:
        asset_group = AssetGroup.objects.get(id=group_id)
        res['content'] += '%s   ' % asset_group.name
        asset_group.delete()

    return HttpResponse(u'删除成功')


@require_role('admin')
@user_operator_record
def asset_add(request,res, *args):
    """
    Asset add view
    添加资产
    """
    error = msg = ''
    header_title, path1, path2 = u'添加资产', u'资产管理', u'添加资产'
    proxys = Proxy.objects.all()
    res['operator'] = path2
    proxy_profiles = gen_proxy_profiles(proxys)
    af = AssetForm()
    nfg = NetWorkingGlobalForm()
    nf = NetWorkingForm()
    pf = PowerManageForm()
    asset_groups = AssetGroup.objects.all()
    if request.method == 'POST':
        try:
            hostname = request.POST.get('name', '')
            if Asset.objects.filter(name=unicode(hostname)):
                error = u'该主机名 %s 已存在!' % hostname
                raise ServerError(error)
            name = request.POST.get('name')
            timestamp = int(time.time())
            id_unique = name + '_'+ str(timestamp)
            fields = {
                "id_unique": id_unique,
                "name": request.POST.get('name'),
                "hostname": request.POST.get('hostname'),
                "profile": request.POST.get('profile'),
                "gateway": request.POST.get('gateway'),
                "power_type": request.POST.get('power_type'),
                "power_address": request.POST.get('power_address'),
                "power_user": request.POST.get('power_username'),
                "power_pass": request.POST.get('power_password'),
                "interfaces": {
                    "eth0":{
                        "mac_address": request.POST.get('mac_address'),
                        "ip_address": request.POST.get('ip_address'),
                        "if_gateway": request.POST.get('per_gateway'),
                        "mtu": request.POST.get('mtu'),
                        "static": 1,
                    },
                }
            }

            data = json.dumps(fields)
            select_proxy = get_object(Proxy, id=int(request.POST.get('proxy')))
            pro_username = select_proxy.username
            pro_password = select_proxy.password
            pro_url = select_proxy.url
            try:
                api = APIRequest('{0}/v1.0/system/'.format(pro_url), pro_username, CRYPTOR.decrypt(pro_password))
                result, codes = api.req_post(data)
            except Exception as e:
                res['flag'] = 'false'
                error = e
                res['content'] = error
            else:
                if codes == 200:
                    msg = result['messege']
                    res['content'] = u'创建主机成功'
                    asset_info = Asset()
                    asset_info.id_unique = id_unique
                    asset_info.name = request.POST.get('name', '')
                    asset_info.profile = request.POST.get('profile', '')
                    asset_info.status = request.POST.get('status', '1')
                    asset_info.kickstart = request.POST.get('kickstart', '')
                    asset_info.port = request.POST.get('port',22)
                    asset_info.username = request.POST.get('username', 'rooot')
                    pwd = request.POST.get('password', '')
                    asset_info.password = CRYPTOR.encrypt(pwd)
                    asset_info.idc_id = int(request.POST.get('idc', '1'))
                    asset_info.cabinet = request.POST.get('cabinet', '')
                    asset_info.number = request.POST.get('number', '')
                    asset_info.machine_status = int(request.POST.get('machine_status', 1))
                    asset_info.asset_type = int(request.POST.get('asset_type', 1))
                    asset_info.sn = request.POST.get('sn', '')
                    asset_info.comment = request.POST.get('comment', '')
                    asset_info.proxy_id = int(request.POST.get('proxy', '1'))

                    nt_g = NetWorkingGlobal()
                    nt_g.hostname = request.POST.get('hostname', '')
                    nt_g.gateway = request.POST.get('gateway','')
                    nt_g.name_servers = request.POST.get('name_servers', '')
                    nt_g.save()
                    asset_info.networking_g_id = nt_g.id

                    pm = PowerManage()
                    pm.power_type = request.POST.get('power_type')
                    pm.power_address = request.POST.get('power_address')
                    pm.power_username = request.POST.get('power_username')
                    pm.power_password = request.POST.get('power_password')
                    pm.save()
                    asset_info.power_manage_id = pm.id

                    asset_info.proxy_id = int(request.POST.get('proxy', 1))
                    is_active = True if request.POST.get('is_active', '1') == '1' else False
                    is_enabled = True if request.POST.get('is_enabled', '1') == '1' else False
                    asset_info.netboot_enabled = is_enabled
                    asset_info.is_active = is_active
                    asset_info.save()

                    net = NetWorking()
                    net.net_name = request.POST.get('net_name', '')
                    net.mac_address = request.POST.get('mac_address', '')
                    net.ip_address = request.POST.get('ip_address','')
                    net.dns_name = request.POST.get('dns_name', '')
                    net.mtu = request.POST.get('mtu', '')
                    net.per_gateway = request.POST.get('per_gateway', '')
                    net.static = request.POST.get('static', '')
                    net.static_routes = request.POST.get('static_routes', '')
                    net.subnet_mask = request.POST.get('subnet_mask', '')
                    net.save()
                    asset_info.networking.add(net)

                    group = AssetGroup()
                    group_id = request.POST.getlist('group')
                    for item in group_id:
                        group = AssetGroup.objects.get(id=int(item))
                        asset_info.group.add(group)
                else:
                    res['flag'] = 'false'
                    error = "创建机器失败:%s"%result['messege']
        except ServerError:
            res['flag'] = 'false'
            res['content'] = error

    return my_render('assetManage/asset_add.html', locals(), request)


@require_role('admin')
def asset_add_batch(request):
    header_title, path1, path2 = u'添加资产', u'资产管理', u'批量添加'
    return my_render('assetManage/asset_add_batch.html', locals(), request)


@require_role('admin')
@user_operator_record
def asset_del(request,res, *args):
    """
    del a asset
    删除主机
    """
    response = {'msg': u'删除成功'}
    res['operator'] = res['content'] = u'删除主机'
    asset_id = request.GET.get('id', '')
    if asset_id:
        asset = get_object(Asset, id=int(asset_id))
        if asset:
            proxy = asset.proxy
            param = {'names': [asset.name], 'id_unique': asset.id_unique}
            data = json.dumps(param)
            try:
                api = APIRequest('{0}/v1.0/system'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
                result, code = api.req_del(data)
                logger.debug(u'删除单一资产result:%s'%result)
                if code == 200:
                    asset.delete()
                else:
                    response['msg'] = result['messege']
            except Exception as e:
                logger.error(e)
                res['flag'] = 'false'
                res['content'] = e
                response['msg'] = e

    if request.method == 'POST':
        asset_batch = request.GET.get('arg', '')
        asset_id_all = request.POST.get('asset_id_all', '')
        asset_list = []
        if asset_batch:
            for asset_id in asset_id_all.split(','):
                asset = get_object(Asset, id=int(asset_id))
                res['content'] += '%s   ' % asset.name
                if asset:
                    asset_list.append(asset)
            asset_proxys = gen_asset_proxy(asset_list)
            for key, value in asset_proxys.items():
                asset_names = [asset.name for asset in value]
                id_uniques = [asset.id_unique for asset in value]
                param = {'names': asset_names, 'id_unique': id_uniques}
                data = json.dumps(param)
                proxy_obj = Proxy.objects.get(proxy_name=key)
                try:
                    api = APIRequest('{0}/v1.0/system'.format(proxy_obj.url), proxy_obj.username, CRYPTOR.decrypt(proxy_obj.password))
                    result, code = api.req_del(data)
                    logger.debug(u'删除多个资产result:%s'% result)
                    if code == 200:
                        for item in value:
                            item.delete()
                    else:
                        response['msg'] = result['messege']
                except Exception as e:
                    logger.error(e)
                    res['flag'] = 'false'
                    res['content'] = e
                    response['msg'] = e
    return HttpResponse(json.dumps(response), content_type='application/json')


@require_role(role='super')
@user_operator_record
def asset_edit(request, res, *args):
    """
    edit a asset
    修改主机
    """
    error = msg = ''
    header_title, path1, path2 = u'修改资产', u'资产管理', u'修改资产'
    res['operator'] = path2
    asset_id = request.GET.get('id', '')
    username = request.user.username
    asset_info = get_object(Asset, id=asset_id)
    asset_password = CRYPTOR.decrypt(asset_info.password)
    id_unique = asset_info.id_unique
    proxys = Proxy.objects.all()
    proxy_profiles = gen_proxy_profiles(proxys)
    af = AssetForm(instance=asset_info)
    nf = NetWorkingForm(instance=asset_info.networking.all()[0])
    nfg = NetWorkingGlobalForm(instance=asset_info.networking_g)
    pf = PowerManageForm(instance=asset_info.power_manage)
    if request.method == 'POST':
        try:
            asset_info.name = request.POST.get('name', '')
            asset_info.profile = request.POST.get('profile', '')
            asset_info.kickstart = request.POST.get('kickstart', '')
            asset_info.port = request.POST.get('port',22)
            asset_info.username = request.POST.get('username', 'root')
            pwd = request.POST.get('password', '')
            asset_info.password = CRYPTOR.encrypt(pwd)
            asset_info.idc_id = int(request.POST.get('idc', '1'))
            asset_info.cabinet = request.POST.get('cabinet', '')
            asset_info.number = request.POST.get('number', '')
            asset_info.machine_status = int(request.POST.get('machine_status', 1))
            asset_info.asset_type = int(request.POST.get('asset_type', 1))
            asset_info.comment = request.POST.get('comment', '')
            asset_info.proxy_id = int(request.POST.get('proxy', '1'))

            nt_g = asset_info.networking_g
            nt_g.hostname = request.POST.get('hostname', '')
            nt_g.gateway = request.POST.get('gateway', '')
            nt_g.name_servers = request.POST.get('name_servers', '')
            nt_g.save()

            pm = asset_info.power_manage
            pm.power_type = request.POST.get('power_type')
            pm.power_address = request.POST.get('power_address')
            pm.power_username = request.POST.get('power_username')
            pm.power_password = request.POST.get('power_password')
            pm.save()

            asset_info.proxy_id = int(request.POST.get('proxy', 1))
            is_active = True if request.POST.get('is_active', '1') == '1' else False
            is_enabled = True if request.POST.get('is_enabled', '1') == '1' else False
            asset_info.netboot_enabled = is_enabled
            asset_info.is_active = is_active

            net = asset_info.networking.all()[0]
            net.net_name = request.POST.get('net_name', '')
            net.mac_address = request.POST.get('mac_address', '')
            net.ip_address = request.POST.get('ip_address','')
            net.dns_name = request.POST.get('dns_name', '')
            net.mtu = request.POST.get('mtu', '')
            net.per_gateway = request.POST.get('per_gateway', '')
            net.static = request.POST.get('static', '')
            net.static_routes = request.POST.get('static_routes', '')
            net.subnet_mask = request.POST.get('subnet_mask', '')
            net.save()

            group = AssetGroup()
            group_id = request.POST.getlist('group')
            for item in group_id:
                group = AssetGroup.objects.get(id=int(item))
                asset_info.group.add(group)
            asset_info.save()
        except ServerError:
            res['flag'] = 'false'
            res['content'] = error
        else:
            name = request.POST.get('name')
            res['content'] = 'edit %s success' % name

            fields = {
                'id_unique': id_unique,
                "hostname": request.POST.get('hostname'),
                "profile": request.POST.get('profile'),
                "gateway": request.POST.get('gateway'),
                "power_type": request.POST.get('power_type'),
                "power_address": request.POST.get('power_address'),
                "power_user": request.POST.get('power_username'),
                "power_pass": request.POST.get('power_password'),
                "interfaces": {
                    "eth0":{
                        "mac_address": request.POST.get('mac_address'),
                        "ip_address": request.POST.get('ip_address'),
                        "if_gateway": request.POST.get('per_gateway'),
                        "mtu": request.POST.get('mtu'),
                        "static": 1,
                    },
                }
            }
            data = json.dumps(fields)
            select_proxy = get_object(Proxy, id=int(request.POST.get('proxy')))
            pro_username = select_proxy.username
            pro_password = select_proxy.password
            pro_url = select_proxy.url
            try:
                api = APIRequest('{0}/v1.0/system/{1}'.format(pro_url, name), pro_username, CRYPTOR.decrypt(pro_password))
                result, code = api.req_put(data)
            except Exception, e:
                    error = e
            else:
                if code == 200:
                    msg = result['messege']
                else:
                    error = result['messege']

    return my_render('assetManage/asset_edit.html', locals(), request)


@require_role('user')
def asset_list(request):
    """
    asset list view
    """
    header_title, path1, path2 = u'查看资产', u'资产管理', u'查看资产'
    username = request.user.username
    user_perm = request.session['role_id']
    idc_all = IDC.objects.filter()
    asset_group_all = AssetGroup.objects.all()
    asset_types = ASSET_TYPE
    asset_status = ASSET_STATUS
    idc_name = request.GET.get('idc', '')
    group_name = request.GET.get('group', '')
    asset_type = request.GET.get('asset_type', '')
    status = request.GET.get('status', '')
    keyword = request.GET.get('keyword', '')
    export = request.GET.get("export", False)
    group_id = request.GET.get("group_id", '')
    idc_id = request.GET.get("idc_id", '')
    asset_id_all = request.GET.getlist("id", '')

    if group_id:
        group = get_object(AssetGroup, id=group_id)
        if group:
            asset_find = Asset.objects.filter(group=group)
    elif idc_id:
        idc = get_object(IDC, id=idc_id)
        if idc:
            asset_find = Asset.objects.filter(idc=idc)
    else:
        if user_perm != 0:
            asset_find = Asset.objects.all()
        else:
            asset_id_all = []
            user = get_object(User, username=username)
            asset_perm = get_group_user_perm(user) if user else {'asset': ''}
            user_asset_perm = asset_perm['asset'].keys()
            for asset in user_asset_perm:
                asset_id_all.append(asset.id)
            asset_find = Asset.objects.filter(pk__in=asset_id_all)
            asset_group_all = list(asset_perm['asset_group'])

    if idc_name:
        asset_find = asset_find.filter(idc__name__contains=idc_name)

    if group_name:
        asset_find = asset_find.filter(group__name__contains=group_name)

    if asset_type:
        asset_find = asset_find.filter(asset_type__contains=asset_type)

    if status:
        asset_find = asset_find.filter(status__contains=status)

    if keyword:
        asset_find = asset_find.filter(
            Q(hostname__contains=keyword) |
            Q(other_ip__contains=keyword) |
            Q(ip__contains=keyword) |
            Q(remote_ip__contains=keyword) |
            Q(comment__contains=keyword) |
            Q(username__contains=keyword) |
            Q(group__name__contains=keyword) |
            Q(cpu__contains=keyword) |
            Q(memory__contains=keyword) |
            Q(disk__contains=keyword) |
            Q(brand__contains=keyword) |
            Q(cabinet__contains=keyword) |
            Q(sn__contains=keyword) |
            Q(system_type__contains=keyword) |
            Q(system_version__contains=keyword))

    if export:
        if asset_id_all:
            asset_find = []
            for asset_id in asset_id_all:
                asset = get_object(Asset, id=asset_id)
                if asset:
                    asset_find.append(asset)
        s = write_excel(asset_find)
        if s[0]:
            file_name = s[1]
        smg = u'excel文件已生成，请点击下载!'
        return my_render('assetManage/asset_excel_download.html', locals(), request)
    assets_list, p, assets, page_range, current_page, show_first, show_end = pages(asset_find, request)
    if user_perm != 0:
        return my_render('assetManage/asset_list.html', locals(), request)
    else:
        return my_render('assetManage/asset_cu_list.html', locals(), request)


@require_role('admin')
def asset_action(request, status):
    result = ''
    if request.method == 'POST':
        select_ids = request.POST.getlist('asset_id_all')
        select_ids = select_ids[0].split(',')
        asset_list = []
        for item in select_ids:
            asset = get_object(Asset, id=int(item))
            asset_list.append(asset)
        asset_proxys = gen_asset_proxy(asset_list)
        for key, value in asset_proxys.items():
            proxy = Proxy.objects.get(proxy_name=key)
            systems = [item.name for item in value]
            profile = asset_list[0].profile
            if status == 'rebuild':
                data = {
                    'rebuild': 'true',
                    'profile': profile,
                    'systems': systems
                }
            else:
                data = {
                    'power': status,
                    'systems': systems
                }
            data = json.dumps(data)
            try:
                api = APIRequest('{0}/v1.0/system/action'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
                result, codes = api.req_post(data)
                logger.debug(u"操作结果result:%s   codes:%s"%(result, codes))
                task = Task()
                task.task_name = result['task_name']
                task.username = request.user.username
                task.status = result['messege']
                task.start_time = datetime.datetime.now()
                task.url = '{0}/v1.0/system/action'.format(proxy.url)
                task.save()
                task_queue.put(dict(task_name=result['task_name'], task_user=request.user.username, task_proxy=proxy.proxy_name))
            except Exception as e:
                logger.debug(e)
        return HttpResponse(json.dumps(result), content_type='application/json')


@require_role('admin')
def asset_event(request):
    response = {'error': '', 'message':''}
    if request.method == 'GET':
        user_name = request.user.username
        try:
            if task_queue.qsize() > 0:
                tk_event = task_queue.get()
                while tk_event['task_user'] != user_name:
                    tk_event = task_queue.get()
                tk_proxy = Proxy.objects.get(proxy_name=tk_event['task_proxy'])
                api = APIRequest('{0}/v1.0/event/{1}'.format(tk_proxy.url, tk_event['task_name']), tk_proxy.username, CRYPTOR.decrypt(tk_proxy.password))
                result, codes = api.req_get()
                logger.debug(u'事件查询结果result:%s'%result)
                tk = get_object(Task, task_name=tk_event['task_name'])
                tk.status = result['status']
                tk.content = result['event_log']
                tk.save()
                response['message'] = result['event_log']
                return HttpResponse(json.dumps(response), content_type='application/json')
        except Exception as e:
            response['error'] = e
            return HttpResponse(json.dumps(response), content_type='application/json')



@require_role('admin')
@user_operator_record
def asset_edit_batch(request, res, *args):
    res['operator'] = res['content'] =u'修改主机'
    af = AssetForm()
    name = request.user.username
    asset_group_all = AssetGroup.objects.all()

    if request.method == 'POST':
        env = request.POST.get('env', '')
        idc_id = request.POST.get('idc', '')
        port = request.POST.get('port', '')
        use_default_auth = request.POST.get('use_default_auth', '')
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        group = request.POST.getlist('group', [])
        cabinet = request.POST.get('cabinet', '')
        comment = request.POST.get('comment', '')
        asset_id_all = unicode(request.GET.get('asset_id_all', ''))
        asset_id_all = asset_id_all.split(',')
        for asset_id in asset_id_all:
            alert_list = []
            asset = get_object(Asset, id=asset_id)
            if asset:
                if env:
                    if asset.env != env:
                        asset.env = env
                        alert_list.append([u'运行环境', asset.env, env])
                if idc_id:
                    idc = get_object(IDC, id=idc_id)
                    name_old = asset.idc.name if asset.idc else u''
                    if idc and idc.name != name_old:
                        asset.idc = idc
                        alert_list.append([u'机房', name_old, idc.name])
                if port:
                    if unicode(asset.port) != port:
                        asset.port = port
                        alert_list.append([u'端口号', asset.port, port])

                if use_default_auth:
                    if use_default_auth == 'default':
                        asset.use_default_auth = 1
                        asset.username = ''
                        asset.password = ''
                        alert_list.append([u'使用默认管理账号', asset.use_default_auth, u'默认'])
                    elif use_default_auth == 'user_passwd':
                        asset.use_default_auth = 0
                        asset.username = username
                        password_encode = CRYPTOR.encrypt(password)
                        asset.password = password_encode
                        alert_list.append([u'使用默认管理账号', asset.use_default_auth, username])
                if group:
                    group_new, group_old, group_new_name, group_old_name = [], asset.group.all(), [], []
                    for group_id in group:
                        g = get_object(AssetGroup, id=group_id)
                        if g:
                            group_new.append(g)
                    if not set(group_new) < set(group_old):
                        group_instance = list(set(group_new) | set(group_old))
                        for g in group_instance:
                            group_new_name.append(g.name)
                        for g in group_old:
                            group_old_name.append(g.name)
                        asset.group = group_instance
                        alert_list.append([u'主机组', ','.join(group_old_name), ','.join(group_new_name)])
                if cabinet:
                    if asset.cabinet != cabinet:
                        asset.cabinet = cabinet
                        alert_list.append([u'机柜号', asset.cabinet, cabinet])
                if comment:
                    if asset.comment != comment:
                        asset.comment = comment
                        alert_list.append([u'备注', asset.comment, comment])
                asset.save()
                res['content'] += '[%s]   ' % asset.name
            if alert_list:
                recode_name = unicode(name) + ' - ' + u'批量'
                AssetRecord.objects.create(asset=asset, username=recode_name, content=alert_list)
        return my_render('assetManage/asset_update_status.html', locals(), request)

    return my_render('assetManage/asset_edit_batch.html', locals(), request)


@require_role('admin')
def asset_detail(request):
    """
    Asset detail view
    """
    header_title, path1, path2 = u'主机详细信息', u'资产管理', u'主机详情'
    asset_id = request.GET.get('id', '')
    asset = get_object(Asset, id=asset_id)
    perm_info = get_group_asset_perm(asset)
    log = Log.objects.filter(host=asset.name)
    if perm_info:
        user_perm = []
        for perm, value in perm_info.items():
            if perm == 'user':
                for user, role_dic in value.items():
                    user_perm.append([user, role_dic.get('role', '')])
            elif perm == 'user_group' or perm == 'rule':
                user_group_perm = value
    print perm_info

    asset_record = AssetRecord.objects.filter(asset=asset).order_by('-alert_time')

    return my_render('assetManage/asset_detail.html', locals(), request)


@require_role('admin')
@user_operator_record
def asset_update(request,res, *args):
    """
    Asset update host info via ansible view
    """
    res['operator'] = u'更新主机'
    asset_id = request.GET.get('id', '')
    asset = get_object(Asset, id=int(asset_id))
    name = request.user.username
    if not asset:
        res['flag'] = 'false'
        res['content'] = u'主机[%s]不存在' % asset.name
        return HttpResponseRedirect(reverse('asset_detail')+'?id=%s' % asset_id)
    else:
        asset_ansible_update([asset], name)
        res['content'] = u'更新主机[%s]' % asset.name
    return HttpResponseRedirect(reverse('asset_detail')+'?id=%s' % asset_id)


@require_role('admin')
@user_operator_record
def asset_update_batch(request,res,*args):
    response = {'success':'', 'error':''}
    res['operator'] = res['content'] = u'批量更新主机'
    if request.method == 'POST':
        try:
            arg = request.GET.get('arg', '')
            name = unicode(request.user.username) + ' - ' + u'自动更新'
            if arg == 'all':
                asset_list = Asset.objects.all()
            else:
                asset_list = []
                asset_id_all = request.POST.get('asset_id_all', '')
                asset_id_all = asset_id_all.split(',')
                for asset_id in asset_id_all:
                    asset = Asset.objects.get(id=int(asset_id))
                    if asset:
                        asset_list.append(asset)
            asset_proxys = gen_asset_proxy(asset_list)
            for key, value in asset_proxys.items():
                host_list = [asset.networking.all()[0].ip_address for asset in value]
                proxy = Proxy.objects.get(proxy_name=key)
                resource = gen_resource(value)
                data = {'mod_name': 'setup',
                        'resource': resource,
                        'hosts': host_list,
                        'mod_args': '',
                        'action': 'update',
                        }
                data = json.dumps(data)
                api = APIRequest('{0}/v1.0/module'.format(proxy.url), proxy.username, CRYPTOR.decrypt(proxy.password))
                result, code = api.req_post(data)
                logger.debug(u'更新操作结果result:%s       code:%s' % (result,code))
                if code == 200:
                    asset_ansible_update(value, result, name)
                    for asset in value:
                        res['content'] += ' [%s] '% asset.name
                    response['success'] = u'批量更新成功!'
        except Exception as e:
            logger.error(e)
            res['flag'] = 'false'
            res['content'] = u'批量更新失败'
            response['error'] = e
        return HttpResponse(json.dumps(response), content_type='application/json')


@require_role('admin')
@user_operator_record
def idc_add(request,res, *args):
    """
    IDC add view
    """
    header_title, path1, path2 = u'添加IDC', u'资产管理', u'添加IDC'
    res['operator'] = path2
    if request.method == 'POST':
        idc_form = IdcForm(request.POST)
        if idc_form.is_valid():
            idc_name = idc_form.cleaned_data['name']

            if IDC.objects.filter(name=idc_name):
                emg = u'添加失败, 此IDC [%s] 已存在!' % idc_name
                res['flag'] = 'false'
                res['content'] = emg
                return my_render('assetManage/idc_add.html', locals(), request)
            else:
                idc_form.save()
                smg = u'IDC: [%s]添加成功' % idc_name
                res['content'] = smg
            return HttpResponseRedirect(reverse('idc_list'))
    else:
        idc_form = IdcForm()
    return my_render('assetManage/idc_add.html', locals(), request)


@require_role('admin')
def idc_list(request):
    """
    IDC list view
    """
    header_title, path1, path2 = u'查看IDC', u'资产管理', u'查看IDC'
    posts = IDC.objects.all()
    keyword = request.GET.get('keyword', '')
    if keyword:
        posts = IDC.objects.filter(Q(name__contains=keyword) | Q(comment__contains=keyword))
    else:
        posts = IDC.objects.exclude(name='ALL').order_by('id')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return my_render('assetManage/idc_list.html', locals(), request)


@require_role('admin')
@user_operator_record
def idc_edit(request, res, *args):
    """
    IDC edit view
    """
    header_title, path1, path2 = u'编辑IDC', u'资产管理', u'编辑IDC'
    res['operator'] = path2
    idc_id = request.GET.get('id', '')
    idc = get_object(IDC, id=idc_id)
    if request.method == 'POST':
        idc_form = IdcForm(request.POST, instance=idc)
        if idc_form.is_valid():
            res['content'] = u'编辑IDC[%s]' % idc.name
            idc_form.save()
            return HttpResponseRedirect(reverse('idc_list'))
    else:
        idc_form = IdcForm(instance=idc)
        return my_render('assetManage/idc_edit.html', locals(), request)


@require_role('admin')
@user_operator_record
def idc_del(request,res, *args):
    """
    IDC delete view
    """
    res['operator'] = res['content'] = u'删除机房'
    idc_ids = request.GET.get('id', '')
    idc_id_list = idc_ids.split(',')

    for idc_id in idc_id_list:
        idc = IDC.objects.get(id=idc_id)
        res['content'] += '  [%s]  ' % idc.name

    return HttpResponseRedirect(reverse('idc_list'))


@require_role('admin')
@user_operator_record
def asset_upload(request,res, *args):
    """
    Upload asset excel file view
    """
    res['operator'] = u'批量添加主机'
    if request.method == 'POST':
        excel_file = request.FILES.get('file_name', '')
        ret, asset_name_list = excel_to_db(excel_file)
        if ret:
            smg = u'批量添加成功'
            for item in asset_name_list:
                res['content'] += " [%s] " % item

        else:
            emg = u'批量添加失败,请检查格式.'
            res['flag'] = 'false'
            res['content'] = emg
    return my_render('assetManage/asset_add_batch.html', locals(), request)
