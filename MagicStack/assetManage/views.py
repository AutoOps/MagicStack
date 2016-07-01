# -*- coding:utf-8 -*-

from django.db.models import Q
from assetManage.asset_api import *
from MagicStack.api import *
from assetManage.forms import AssetForm, IdcForm,NetWorkingForm,NetWorkingGlobalForm,PowerManageForm
from assetManage.models import *
from permManage.perm_api import get_group_asset_perm, get_group_user_perm, gen_resource
from userManage.user_api import user_operator_record
from common.interface import APIRequest
from common.models import Task
import Queue
import time

task_queue = Queue.Queue()
ASSET_STATUS = {'1': u"已使用", '2': u"未使用" , '3': u"报废"}
ASSET_TYPE = {
    '1': u"物理机",
    '2': u"虚拟机",
    '3': u"交换机",
    '4': u"路由器",
    '5': u"防火墙",
    '6': u"Docker",
    '7': u"其他"
}
POWER_TYPE = {
    'ipmilan': 'ipmilan',
    'drac5': 'drac5',
    'idrac': 'idrac',
    'ilo': 'ilo',
    'ilo2': 'ilo2',
    'ilo3': 'ilo3',
    'ilo4': 'ilo4',
    'intelmodular': 'intelmodular',
}

@require_role('admin')
@user_operator_record
def group_add(request, res,*args):
    """
    Group add view
    添加资产组
    """
    response = {'success': False, 'error': ''}
    res['operator'] = u'添加资产组'
    if request.method == 'POST':
        name = request.POST.get('name', '')
        asset_select = request.POST.getlist('select_multi', [])
        comment = request.POST.get('comment', '')

        try:
            if not name:
                raise ServerError(u'组名不能为空')

            asset_group_test = get_object(AssetGroup, name=name)
            if asset_group_test:
                raise ServerError(u"组名 %s 已存在" % name)

        except ServerError as e:
            res['flag'] = 'false'
            res['content'] = e.message
            response['error'] = e.message

        else:
            db_add_group(name=name, comment=comment, asset_select=asset_select)
            smg = u"添加主机组[%s]成功" % name
            res['content'] = smg
            response['success'] = True
            response['error'] = smg

    return HttpResponse(json.dumps(response), content_type='application/json')


@require_role('admin')
@user_operator_record
def group_edit(request,res, *args):
    """
    Group edit view
    编辑资产组
    """
    res['operator'] = u'编辑主机组'
    if request.method == 'GET':
        try:
            group_id = request.GET.get('id', '')
            if not group_id:
                return HttpResponse(u'资产组ID为空')
            group = get_object(AssetGroup, id=int(group_id))
            if group:
                rest = dict()
                rest["Id"] = group.id
                rest["name"] = group.name
                rest["comment"] = group.comment
                rest["asset_group"] = ','.join([str(item.id) for item in group.asset_set.all()])
                return HttpResponse(json.dumps(rest), content_type='application/json')
            else:
                return HttpResponse(u'资产组不存在')
        except Exception as e:
            logger.error(e)
            return HttpResponse(e)
    else:
        response = {'success': False, 'error': ''}
        group_id = request.GET.get('id', '')
        if not group_id:
            return HttpResponse(u'资产组ID为空')
        group = AssetGroup.objects.get(id=int(group_id))
        name = request.POST.get('name', '')
        asset_select = request.POST.getlist('select_multi', [])
        comment = request.POST.get('comment', '')

        try:
            if not name:
                raise ServerError(u'组名不能为空')

            if AssetGroup.objects.filter(name=name).count() > 1:
                raise ServerError(u"该组名 %s 已存在" % name)
        except ServerError as e:
            res['flag'] = 'false'
            res['content'] = e
            response['error'] = u"添加资产组失败:%s" % e.message
        else:
            group.asset_set.clear()
            db_update_group(id=group_id, name=name, comment=comment, asset_select=asset_select)
            smg = u"主机组 %s 添加成功" % name
            response['success'] = True
            res['content'] = response['error'] = smg
        return HttpResponse(json.dumps(response), content_type='application/json')


@require_role('admin')
def group_list(request):
    """
    list asset group
    列出资产组
    """
    header_title, path1, path2 = u'查看资产组', u'资产管理', u'查看资产组'
    asset_group_list = AssetGroup.objects.all()
    asset_all = Asset.objects.all()
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
        asset_group = AssetGroup.objects.get(id=int(group_id))
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
    asset_status = ASSET_STATUS
    asset_type = ASSET_TYPE
    power_type = POWER_TYPE
    group_all = AssetGroup.objects.all()
    idc_all = IDC.objects.all()
    if request.method == 'POST':
        try:
            hostname = request.POST.get('name', '')
            if Asset.objects.filter(name=unicode(hostname)):
                error = u'该主机名 %s 已存在!' % hostname
                raise ServerError(error)

            name = request.POST.get('name')
            port = request.POST.get('port')
            username = request.POST.get('username')
            pwd = request.POST.get('password')
            hostname = request.POST.get('hostname', '')
            power_address = request.POST.get('power_address')
            power_username = request.POST.get('power_username')
            ency_password = request.POST.get('power_password')
            mac_address = request.POST.get('mac_address')
            ip_address = request.POST.get('ip_address')

            if '' in [name, port, username, pwd, hostname, power_address, power_username, ency_password, mac_address, ip_address]:
                raise ServerError(u'必要参数为空')

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
                error = e.message
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
                    asset_info.port = int(request.POST.get('port',22))
                    asset_info.username = request.POST.get('username', 'root')
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
                    ency_password = CRYPTOR.encrypt(request.POST.get('power_password', ''))
                    pm.power_password = ency_password
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
                    error = u"创建机器失败:%s"%result['messege']
                    res['content'] = error
        except ServerError as e:
            res['flag'] = 'false'
            res['content'] = e.message
            error = e.message

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
    group_all = AssetGroup.objects.all()
    idc_all = IDC.objects.all()
    select_groups = asset_info.group.all()
    asset_status = ASSET_STATUS
    asset_type = ASSET_TYPE
    power_type = POWER_TYPE
    machine_status = str(asset_info.machine_status)
    machine_type = str(asset_info.asset_type)
    id_unique = asset_info.id_unique
    proxys = Proxy.objects.all()
    proxy_profiles = gen_proxy_profiles(proxys)
    nt_g = asset_info.networking_g
    pm = asset_info.power_manage
    power_t = pm.power_type
    net = asset_info.networking.all()[0]
    if request.method == 'POST':
        try:
            asset_info.name = request.POST.get('name', '')
            asset_info.profile = request.POST.get('profile', '')
            asset_info.kickstart = request.POST.get('kickstart', '')
            asset_info.port = int(request.POST.get('port',22))
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


            nt_g.hostname = request.POST.get('hostname', '')
            nt_g.gateway = request.POST.get('gateway', '')
            nt_g.name_servers = request.POST.get('name_servers', '')
            nt_g.save()

            pm.power_type = request.POST.get('power_type')
            pm.power_address = request.POST.get('power_address')
            pm.power_username = request.POST.get('power_username')
            ency_password = CRYPTOR.encrypt(request.POST.get('power_password', ''))
            pm.power_password = ency_password
            pm.save()

            asset_info.proxy_id = int(request.POST.get('proxy', 1))
            is_active = True if request.POST.get('is_active', '1') == '1' else False
            is_enabled = True if request.POST.get('is_enabled', '1') == '1' else False
            asset_info.netboot_enabled = is_enabled
            asset_info.is_active = is_active

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
            res['content'] = u'编辑资产[%s]成功' % name

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
    asset_list = Asset.objects.all()

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


@require_role('user')
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
def asset_detail(request):
    """
    Asset detail view
    """
    header_title, path1, path2 = u'主机详细信息', u'资产管理', u'主机详情'
    asset_id = request.GET.get('id', '')
    asset = get_object(Asset, id=asset_id)
    perm_info = get_group_asset_perm(asset)
    log = Log.objects.filter(host=asset.networking.all()[0].ip_address).order_by('-start_time')[0:10]
    if perm_info:
        user_perm = []
        for perm, value in perm_info.items():
            if perm == 'user':
                for user, role_dic in value.items():
                    user_perm.append([user, role_dic.get('role', '')])
            elif perm == 'user_group' or perm == 'rule':
                user_group_perm = value

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
        idc.delete()
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
