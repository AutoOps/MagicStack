# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed
from paramiko import SSHException
from permManage.perm_api import *

from userManage.models import User, UserGroup
from userManage.user_api import user_operator_record
from assetManage.models import Asset, AssetGroup
from permManage.models import PermRole, PermRule, PermSudo, PermPush
from MagicStack.models import Setting
import Queue
from permManage.utils import gen_keys, trans_all
from permManage.ansible_api import MyTask
from permManage.perm_api import get_role_info, get_role_push_host,query_event
from MagicStack.api import my_render, get_object, CRYPTOR
from common.models import Task


# 设置PERM APP Log
from MagicStack.api import logger

# 推送用户事件队列
task_queue = Queue.Queue()


@require_role('admin')
def perm_rule_list(request):
    """
    list rule page
    授权规则列表
    """
    # 渲染数据
    header_title, path1, path2 = "授权规则", "规则管理", "查看规则"
    # 获取所有规则
    rules_list = PermRule.objects.all()
    rule_id = request.GET.get('id')
    # TODO: 搜索和分页
    keyword = request.GET.get('search', '')
    if rule_id:
        rules_list = rules_list.filter(id=rule_id)

    if keyword:
        rules_list = rules_list.filter(Q(name=keyword))

    rules_list, p, rules, page_range, current_page, show_first, show_end = pages(rules_list, request)

    return my_render('permManage/perm_rule_list.html', locals(), request)


@require_role('admin')
def perm_rule_detail(request):
    """
    rule detail page
    授权详情
    """
    # 渲染数据
    header_title, path1, path2 = "授权规则", "规则管理", "规则详情"

    # 根据rule_id 取得rule对象
    try:
        if request.method == "GET":
            rule_id = request.GET.get("id")
            if not rule_id:
                raise ServerError("Rule Detail - no rule id get")
            rule_obj = PermRule.objects.get(id=rule_id)
            user_obj = rule_obj.user.all()
            user_group_obj = rule_obj.user_group.all()
            asset_obj = rule_obj.asset.all()
            asset_group_obj = rule_obj.asset_group.all()
            roles_name = [role.name for role in rule_obj.role.all()]

            # 渲染数据
            roles_name = ','.join(roles_name)
            rule = rule_obj
            users = user_obj
            user_groups = user_group_obj
            assets = asset_obj
            asset_groups = asset_group_obj
    except ServerError, e:
        logger.warning(e)

    return my_render('permManage/perm_rule_detail.html', locals(), request)


@user_operator_record
def perm_rule_add(request, res, *args):
    """
    add rule page
    添加授权
    """
    header_title, path1, path2 = "授权规则", "规则管理", "添加规则"
    res['operator'] = path2
    # 渲染数据, 获取所有 用户,用户组,资产,资产组,用户角色, 用于添加授权规则
    users = User.objects.all()
    user_groups = UserGroup.objects.all()
    assets = Asset.objects.all()
    asset_groups = AssetGroup.objects.all()
    roles = PermRole.objects.all()

    if request.method == 'POST':
        # 获取用户选择的 用户,用户组,资产,资产组,用户角色
        users_select = request.POST.getlist('user', [])  # 需要授权用户
        user_groups_select = request.POST.getlist('user_group', [])  # 需要授权用户组
        assets_select = request.POST.getlist('asset', [])  # 需要授权资产
        asset_groups_select = request.POST.getlist('asset_group', [])  # 需要授权资产组
        roles_select = request.POST.getlist('role', [])  # 需要授权角色
        rule_name = request.POST.get('name')
        rule_comment = request.POST.get('comment')

        try:
            rule = get_object(PermRule, name=rule_name)

            if rule:
                raise ServerError(u'授权规则 %s 已存在' % rule_name)

            if not rule_name or not roles_select:
                raise ServerError(u'系统用户名称和规则名称不能为空')

            # 获取需要授权的主机列表
            assets_obj = [Asset.objects.get(id=asset_id) for asset_id in assets_select]
            asset_groups_obj = [AssetGroup.objects.get(id=group_id) for group_id in asset_groups_select]
            group_assets_obj = []
            for asset_group in asset_groups_obj:
                group_assets_obj.extend(list(asset_group.asset_set.all()))
            calc_assets = set(group_assets_obj) | set(assets_obj)  # 授权资产和资产组包含的资产

            # 获取需要授权的用户列表
            users_obj = [User.objects.get(id=user_id) for user_id in users_select]
            user_groups_obj = [UserGroup.objects.get(id=group_id) for group_id in user_groups_select]

            # 获取授予的角色列表
            roles_obj = [PermRole.objects.get(id=role_id) for role_id in roles_select]
            need_push_asset = set()

            for role in roles_obj:
                asset_no_push = get_role_push_host(role=role)[1]  # 获取某角色已经推送的资产
                need_push_asset.update(set(calc_assets) & set(asset_no_push))
                if need_push_asset:
                    raise ServerError(u'没有推送系统用户 %s 的主机 %s'
                                      % (role.name, ','.join([asset.name for asset in need_push_asset])))

            # 仅授权成功的，写回数据库(授权规则,用户,用户组,资产,资产组,用户角色)
            rule = PermRule(name=rule_name, comment=rule_comment)
            rule.save()
            rule.user = users_obj
            rule.user_group = user_groups_obj
            rule.asset = assets_obj
            rule.asset_group = asset_groups_obj
            rule.role = roles_obj
            rule.save()

            msg = u"添加授权规则：%s" % rule.name
            res['content'] = msg
            return HttpResponseRedirect(reverse('rule_list'))
        except ServerError, e:
            error = e
            res['flag'] = 'false'
            res['content'] = e
    return my_render('permManage/perm_rule_add.html', locals(), request)


@require_role('admin')
@user_operator_record
def perm_rule_edit(request, res, *args):
    """
    edit rule page
    """
    # 渲染数据
    header_title, path1, path2 = "授权规则", "规则管理", "编辑授权规则"
    res['operator'] = path2
    rule_id = request.GET.get("id")
    rule = get_object(PermRule, id=rule_id)

    # 渲染数据, 获取所选的rule对象

    users = User.objects.all()
    user_groups = UserGroup.objects.all()
    assets = Asset.objects.all()
    asset_groups = AssetGroup.objects.all()
    roles = PermRole.objects.all()

    if request.method == 'POST' and rule_id:
        # 获取用户选择的 用户,用户组,资产,资产组,用户角色
        rule_name = request.POST.get('name')
        rule_comment = request.POST.get("comment")
        users_select = request.POST.getlist('user', [])
        user_groups_select = request.POST.getlist('user_group', [])
        assets_select = request.POST.getlist('asset', [])
        asset_groups_select = request.POST.getlist('asset_group', [])
        roles_select = request.POST.getlist('role', [])

        try:
            if not rule_name or not roles_select:
                raise ServerError(u'系统用户和关联系统用户不能为空')

            assets_obj = [Asset.objects.get(id=asset_id) for asset_id in assets_select]
            asset_groups_obj = [AssetGroup.objects.get(id=group_id) for group_id in asset_groups_select]
            group_assets_obj = []
            for asset_group in asset_groups_obj:
                group_assets_obj.extend(list(asset_group.asset_set.all()))
            calc_assets = set(group_assets_obj) | set(assets_obj)  # 授权资产和资产组包含的资产

            # 获取需要授权的用户列表
            users_obj = [User.objects.get(id=user_id) for user_id in users_select]
            user_groups_obj = [UserGroup.objects.get(id=group_id) for group_id in user_groups_select]

            # 获取授予的角色列表
            roles_obj = [PermRole.objects.get(id=role_id) for role_id in roles_select]
            need_push_asset = set()
            for role in roles_obj:
                asset_no_push = get_role_push_host(role=role)[1]  # 获取某角色已经推送的资产
                need_push_asset.update(set(calc_assets) & set(asset_no_push))
                if need_push_asset:
                    raise ServerError(u'没有推送系统用户 %s 的主机 %s'
                                      % (role.name, ','.join([asset.name for asset in need_push_asset])))

                # 仅授权成功的，写回数据库(授权规则,用户,用户组,资产,资产组,用户角色)
                rule.user = users_obj
                rule.user_group = user_groups_obj
                rule.asset = assets_obj
                rule.asset_group = asset_groups_obj
                rule.role = roles_obj
            rule.name = rule_name
            rule.comment = rule_comment
            rule.save()
            msg = u"更新授权规则：%s成功" % rule.name
            res['content'] = msg
        except ServerError, e:
            error = e
            res['flag'] = 'false'
            res['content'] = e

    return my_render('permManage/perm_rule_edit.html', locals(), request)


@require_role('admin')
@user_operator_record
def perm_rule_delete(request, res, *args):
    """
    use to delete rule
    :param request:
    :return:
    """
    res['operator'] = '删除授权规则'
    if request.method == 'POST':
        rule_id = request.POST.get("id")
        rule_obj = PermRule.objects.get(id=rule_id)
        res['content'] = '删除授权规则[%s]' % rule_obj.name
        rule_obj.delete()
        return HttpResponse(u"删除授权规则：%s" % rule_obj.name)
    else:
        res['flag'] = 'false'
        res['content'] = '删除授权规则失败'
        return HttpResponse(u"不支持该操作")


@require_role('admin')
def perm_role_list(request):
    """
    list role page
    """
    # 渲染数据
    header_title, path1, path2 = "系统用户", "系统用户管理", "查看系统用户"

    # 获取所有系统角色
    roles_list = PermRole.objects.all()
    role_id = request.GET.get('id')
    # TODO: 搜索和分页
    keyword = request.GET.get('search', '')
    if keyword:
        roles_list = roles_list.filter(Q(name=keyword))

    if role_id:
        roles_list = roles_list.filter(id=role_id)

    roles_list, p, roles, page_range, current_page, show_first, show_end = pages(roles_list, request)

    return my_render('permManage/perm_role_list.html', locals(), request)


@require_role('admin')
@user_operator_record
def perm_role_add(request, res, *args):
    """
    add role page
    """
    header_title, path1, path2 = "系统用户", "系统用户管理", "添加系统用户"
    res['operator'] = path2
    sudos = PermSudo.objects.all()

    if request.method == "POST":
        name = request.POST.get("role_name", "").strip()
        comment = request.POST.get("role_comment", "")
        password = request.POST.get("role_password", "")
        key_content = request.POST.get("role_key", "")
        sudo_ids = request.POST.getlist('sudo_name')

        try:
            if get_object(PermRole, name=name):
                raise ServerError(u'已经存在该用户 %s' % name)
            if name == "root":
                raise ServerError(u'禁止使用root用户作为系统用户，这样非常危险！')

            if password:
                encrypt_pass = CRYPTOR.encrypt(password)
            else:
                encrypt_pass = CRYPTOR.encrypt(CRYPTOR.gen_rand_pass(20))
            # 生成随机密码，生成秘钥对
            sudos_obj = [get_object(PermSudo, id=sudo_id) for sudo_id in sudo_ids]
            if key_content:
                try:
                    key_path = gen_keys(key=key_content)
                except SSHException, e:
                    raise ServerError(e)
            else:
                key_path = gen_keys()
            logger.debug('generate role key: %s' % key_path)

            #将数据同时保存到proxy上
            data = {'name': name,
                    'password': encrypt_pass,
                    'comment': comment,
                    'key_content': key_content,
                    'sudo_ids': sudo_ids}
            data = json.dumps(data)
            message = save_or_delete('PermRole', data)
            logger.debug('message:%s'%message)
            if message == 'success':
                msg = u"添加系统用户: %s" % name
                res['content'] = msg
                # 将数据保存到magicstack上
                role = PermRole(name=name, comment=comment, password=encrypt_pass, key_path=key_path)
                role.save()
                role.sudo = sudos_obj
            return HttpResponseRedirect(reverse('role_list'))
        except ServerError, e:
            error = e
            res['flag'] = 'false'
            res['content'] = e
    return my_render('permManage/perm_role_add.html', locals(), request)


@require_role('admin')
@user_operator_record
def perm_role_delete(request, res, *args):
    """
    delete role page
    """
    res['operator'] = '删除系统用户'
    if request.method == "GET":
        try:
            # 获取参数删除的role对象
            role_id = request.GET.get("id")
            role = get_object(PermRole, id=role_id)
            if not role:
                logger.warning(u"Delete Role: role_id %s not exist" % role_id)
                raise ServerError(u"role_id %s 无数据记录" % role_id)
            filter_type = request.GET.get("filter_type")
            if filter_type:
                if filter_type == "recycle_assets":
                    recycle_assets = [push.asset for push in role.perm_push.all() if push.success]
                    print recycle_assets
                    recycle_assets_ip = ','.join([asset.name for asset in recycle_assets])
                    return HttpResponse(recycle_assets_ip)
                else:
                    return HttpResponse("no such filter_type: %s" % filter_type)
            else:
                return HttpResponse("filter_type: ?")
        except ServerError, e:
            return HttpResponse(e)
    if request.method == "POST":
        try:
            role_id = request.POST.get("id")
            role = get_object(PermRole, id=role_id)
            if not role:
                logger.warning(u"Delete Role: role_id %s not exist" % role_id)
                raise ServerError(u"role_id %s 无数据记录" % role_id)
            role_key = role.key_path
            recycle_assets = [push.asset for push in role.perm_push.all() if push.success]
            logger.debug(u"delete role %s - delete_assets: %s" % (role.name, recycle_assets))
            if recycle_assets:
                recycle_resource = gen_resource(recycle_assets)
                host_list = [asset.networking.all()[0].ip_address for asset in recycle_assets]
                task = MyTask(recycle_resource, host_list)
                try:
                    msg_del_user = task.del_user(get_object(PermRole, id=role_id).name)
                    msg_del_sudo = task.del_user_sudo(get_object(PermRole, id=role_id).name)
                except Exception, e:
                    logger.warning(u"Recycle Role failed: %s" % e)
                    raise ServerError(u"回收已推送的系统用户失败: %s" % e)
                logger.info(u"delete role %s - execute delete user: %s" % (role.name, msg_del_user))
                logger.info(u"delete role %s - execute delete sudo: %s" % (role.name, msg_del_sudo))
                # TODO: 判断返回结果，处理异常
            # 删除存储的秘钥，以及目录
            try:
                key_files = os.listdir(role_key)
                for key_file in key_files:
                    os.remove(os.path.join(role_key, key_file))
                os.rmdir(role_key)
            except OSError, e:
                logger.warning(u"Delete Role: delete key error, %s" % e)
                raise ServerError(u"删除系统用户key失败: %s" % e)
            logger.info(u"delete role %s - delete role key directory: %s" % (role.name, role_key))
            message = save_or_delete('PermRole',{}, obj_id=role_id, action='delete')
            if message == 'success':
                res['content'] = "删除系统用户: %s成功" % role.name
                role.delete()
            else:
                res['content'] = "删除系统用户: %s失败" % role.name
                res['flag'] = 'false'

            return HttpResponse(u"删除系统用户: %s" % role.name)
        except ServerError, e:
            res['flag'] = 'false'
            res['content'] = "删除系统用户失败: %s" %e
            return HttpResponseBadRequest(u"删除失败, 原因：　%s" % e)
    return HttpResponseNotAllowed(u"仅支持POST")


@require_role('admin')
def perm_role_detail(request):
    """
    the role detail page
        the role_info data like:
            {'asset_groups': [],
            'assets': [<Asset: 192.168.10.148>],
            'rules': [<PermRule: PermRule object>],
            '': [],
            '': [<User: user1>]}
    """
    # 渲染数据
    header_title, path1, path2 = "系统用户", "系统用户管理", "系统用户详情"

    try:
        if request.method == "GET":
            role_id = request.GET.get("id")
            if not role_id:
                raise ServerError("not role id")
            role = get_object(PermRole, id=role_id)
            role_info = get_role_info(role_id)

            # 渲染数据
            rules = role_info.get("rules")
            assets = role_info.get("assets")
            asset_groups = role_info.get("asset_groups")
            users = role_info.get("users")
            user_groups = role_info.get("user_groups")
            pushed_asset, need_push_asset = get_role_push_host(get_object(PermRole, id=role_id))
    except ServerError, e:
        logger.warning(e)

    return my_render('permManage/perm_role_detail.html', locals(), request)


@require_role('admin')
@user_operator_record
def perm_role_edit(request, res, *args):
    """
    edit role page
    """
    # 渲染数据
    header_title, path1, path2 = "系统用户", "系统用户管理", "系统用户编辑"
    res['operator'] = path2
    # 渲染数据
    role_id = request.GET.get("id")
    role = PermRole.objects.get(id=role_id)
    role_pass = CRYPTOR.decrypt(role.password)
    sudo_all = PermSudo.objects.all()
    role_sudos = role.sudo.all()
    sudo_all = PermSudo.objects.all()
    if request.method == "GET":
        return my_render('permManage/perm_role_edit.html', locals(), request)

    if request.method == "POST":
        # 获取 POST 数据
        role_name = request.POST.get("role_name")
        role_password = request.POST.get("role_password")
        role_comment = request.POST.get("role_comment")
        role_sudo_names = request.POST.getlist("sudo_name")
        role_sudos = [PermSudo.objects.get(id=sudo_id) for sudo_id in role_sudo_names]
        key_content = request.POST.get("role_key", "")

        try:
            if not role:
                raise ServerError('该系统用户不能存在')

            if role_name == "root":
                raise ServerError(u'禁止使用root用户作为系统用户，这样非常危险！')

            if role_password:
                encrypt_pass = CRYPTOR.encrypt(role_password)
                role.password = encrypt_pass
            # 生成随机密码，生成秘钥对
            if key_content:
                try:
                    key_path = gen_keys(key=key_content, key_path_dir=role.key_path)
                except SSHException:
                    raise ServerError('输入的密钥不合法')
                logger.debug('Recreate role key: %s' % role.key_path)

            data = {'name': role_name,
                    'password': role_password,
                    'comment': role_comment,
                    'sudo_ids': role_sudo_names,
                    'key_content': key_content}
            data = json.dumps(data)
            message = save_or_delete('PermRole', data, role_id, 'update')
            if message == 'success':
                msg = u"更新系统用户： %s成功" % role.name
                res['content'] = msg
                # 只有proxy上的数据库保存完成后,才会写入本地数据库
                role.name = role_name
                role.comment = role_comment
                role.sudo = role_sudos
                role.save()
            else:
                msg = u"更新系统用户： %s失败" % role.name
                res['content'] = msg
                res['flag'] = 'false'

            return HttpResponseRedirect(reverse('role_list'))
        except ServerError, e:
            error = e
            res['flag'] = 'false'
            res['content'] = e

    return my_render('permManage/perm_role_edit.html', locals(), request)


@require_role('admin')
@user_operator_record
def perm_role_push(request, res, *args):
    """
    the role push page
    """
    # 渲染数据
    header_title, path1, path2 = "系统用户", "系统用户管理", "系统用户推送"
    role_id = request.GET.get('id')
    asset_ids = request.GET.get('asset_id')
    role = get_object(PermRole, id=role_id)
    role_proxy = get_one_or_all('PermRole', role_id)
    logger.debug('role_proxy:%s'%role_proxy)
    if not role_proxy:
        error = u'连接proxy失败,请检查proxy服务是否正常!'
        return my_render('permManage/perm_role_push.html', locals(), request)
    assets = Asset.objects.all()
    asset_groups = AssetGroup.objects.all()
    if asset_ids:
        need_push_asset = [get_object(Asset, id=asset_id) for asset_id in asset_ids.split(',')]

    if request.method == "POST":
        # 获取推荐角色的名称列表
        # 计算出需要推送的资产列表
        asset_ids = request.POST.getlist("assets")
        asset_group_ids = request.POST.getlist("asset_groups")
        assets_obj = [Asset.objects.get(id=asset_id) for asset_id in asset_ids]
        asset_groups_obj = [AssetGroup.objects.get(id=asset_group_id) for asset_group_id in asset_group_ids]
        group_assets_obj = []
        for asset_group in asset_groups_obj:
            group_assets_obj.extend(asset_group.asset_set.all())
        calc_assets = list(set(assets_obj) | set(group_assets_obj))

        push_resource = gen_resource(calc_assets)

        # 调用Ansible API 进行推送
        password_push = True if request.POST.get("use_password") else False
        key_push = True if request.POST.get("use_publicKey") else False
        host_list = [asset.networking.all()[0].ip_address for asset in calc_assets]
        host_names = [asset.name for asset in calc_assets]
        task = MyTask(push_resource, host_list)
        ret = {}

        # 因为要先建立用户，而push key是在 password也完成的情况下的 可选项
        # 1. 以秘钥 方式推送角色
        if key_push:
            ret["pass_push"] = task.add_user(role.name)
            ret["key_push"] = task.push_key(role.name, os.path.join(role_proxy['key_path'], 'id_rsa.pub'))

        # 2. 推送账号密码 <为了安全 系统用户统一使用秘钥进行通信， 不再提供密码方式的推送>
        # elif password_push:
        #     ret["pass_push"] = task.add_user(role.name, CRYPTOR.decrypt(role.password))

        # 3. 推送sudo配置文件
        if key_push:
            sudo_list = set([sudo for sudo in role.sudo.all()])  # set(sudo1, sudo2, sudo3)
            if sudo_list:
                ret['sudo'] = task.push_sudo_file([role], sudo_list)
        logger.debug('ret:%s'%ret)
        event_task_names = []
        msg = 'running'
        # 将事件放进queue
        if ret.has_key('pass_push'):
            tk_pass_push = ret['pass_push']['task_name']
            event_task_names.append(tk_pass_push)
        if ret.has_key('key_push'):
            tk_key_push = ret['key_push']['task_name']
            event_task_names.append(tk_key_push)
        if ret.has_key('sudo'):
            if 'task_name' in ret['sudo']:
                tk_sudo_push = ret['sudo']['task_name']
                event_task_names.append(tk_sudo_push)
        event = dict(push_assets=host_names, role_name=role.name,password_push=password_push, key_push=key_push)
        event['tasks'] = event_task_names
        task_queue.put(event)

        #记录task事件
        for item in event['tasks']:
            tk = Task()
            tk.task_name = item
            tk.status = 'running'
            tk.start_time = datetime.datetime.now()
            tk.username = request.user.username
            tk.save()
    return my_render('permManage/perm_role_push.html', locals(), request)


@require_role('admin')
def push_role_event(request):
    response = {'error': '', 'message':''}
    if request.method == 'GET':
        user_name = request.user.username
        try:
            if task_queue.qsize() > 0:
                tk_event = task_queue.get()
                # while tk_event['task_user'] != user_name:
                #     tk_event = task_queue.get()
                host_names = tk_event.pop('push_assets')
                calc_assets = [Asset.objects.get(name=name) for name in host_names]
                role = PermRole.objects.get(name=tk_event['role_name'])
                password_push = tk_event['password_push']
                key_push = tk_event['key_push']
                success_asset = {}
                failed_asset = {}
                for task_name in tk_event['tasks']:
                    result = query_event(task_name)
                    #更新task的status, result
                    tk = get_object(Task, task_name=task_name)
                    tk.status = 'complete'
                    tk.content = result['messege']
                    tk.save()
                    res = json.loads(result['messege'])
                    if res.get('failed'):
                        for hostname, info in res.get('failed').items():
                            if hostname in failed_asset.keys():
                                if info in failed_asset.get(hostname):
                                    failed_asset[hostname] += info
                            else:
                                failed_asset[hostname] = info
                    if res.get('unreachable'):
                        for hostname, info in res.get('unreachable').items():
                            if hostname in failed_asset.keys():
                                if info in failed_asset.get(hostname):
                                    failed_asset[hostname] += info
                            else:
                                failed_asset[hostname] = info

                    if res.get('success'):
                        for hostname, info in res.get('success').items():
                            if hostname in failed_asset.keys():
                                continue
                            elif hostname in success_asset.keys():
                                if str(info) in success_asset.get(hostname, ''):
                                    success_asset[hostname] += str(info)
                            else:
                                success_asset[hostname] = str(info)

                # 推送成功 回写push表
                for asset in calc_assets:
                    push_check = PermPush.objects.filter(role=role, asset=asset)
                    if push_check:
                        func = push_check.update
                    else:
                        def func(**kwargs):
                            PermPush(**kwargs).save()

                    if failed_asset.get(asset.name):
                        func(is_password=password_push, is_public_key=key_push, role=role, asset=asset, success=False,
                             result=failed_asset.get(asset.hostname))
                    else:
                        func(is_password=password_push, is_public_key=key_push, role=role, asset=asset, success=True)

                if not failed_asset:
                    msg = u'系统用户 %s 推送成功[ %s ]' % (role.name, ','.join(success_asset.keys()))
                    response['message'] = msg
                else:
                    error = u'系统用户 %s 推送失败 [ %s ], 推送成功 [ %s ] 进入系统用户详情，查看失败原因' % (role.name,
                                                                        ','.join(failed_asset.keys()),
                                                                        ','.join(success_asset.keys()))
                    response['message'] = error

                return HttpResponse(json.dumps(response), content_type='application/json')
        except Exception as e:
            response['message'] = e
            return HttpResponse(json.dumps(response), content_type='application/json')


@require_role('admin')
def perm_sudo_list(request):
    """
    list sudo commands alias
    :param request:
    :return:
    """
    # 渲染数据
    header_title, path1, path2 = "Sudo命令", "别名管理", "查看别名"

    # 获取所有sudo 命令别名
    sudos_list = PermSudo.objects.all()

    # TODO: 搜索和分页
    keyword = request.GET.get('search', '')
    if keyword:
        sudos_list = sudos_list.filter(Q(name=keyword))

    sudos_list, p, sudos, page_range, current_page, show_first, show_end = pages(sudos_list, request)

    return my_render('permManage/perm_sudo_list.html', locals(), request)


@require_role('admin')
@user_operator_record
def perm_sudo_add(request, res, *args):
    """
    list sudo commands alias
    """
    # 渲染数据
    header_title, path1, path2 = "Sudo命令", "别名管理", "添加别名"
    res['operator'] = path2
    try:
        if request.method == "POST":
            # 获取参数： name, comment
            name = request.POST.get("sudo_name").strip().upper()
            comment = request.POST.get("sudo_comment").strip()
            commands = request.POST.get("sudo_commands").strip()

            if not name or not commands:
                raise ServerError(u"sudo name 和 commands是必填项!")

            pattern = re.compile(r'[\n,\r]')
            deal_space_commands = list_drop_str(pattern.split(commands), u'')
            deal_all_commands = map(trans_all, deal_space_commands)
            commands = ', '.join(deal_all_commands)
            logger.debug(u'添加sudo %s: %s' % (name, commands))

            if get_object(PermSudo, name=name):
                error = 'Sudo别名 %s已经存在' % name
                res['flag'] = 'false'
                res['content'] = error

            data = {'name': name,
                    'comment': comment,
                    'commands': commands}
            data = json.dumps(data)
            message = save_or_delete('PermSudo', data)
            if message == 'success':
                msg = u"添加Sudo命令别名: %s成功" % name
                res['content'] = msg
                sudo = PermSudo(name=name.strip(), comment=comment, commands=commands)
                sudo.save()
            else:
                msg = u"添加Sudo命令别名: %s失败" % name
                res['flag'] = 'false'
                res['content'] = msg

    except ServerError, e:
        error = e
        res['flag'] = 'false'
        res['content'] = error
    return my_render('permManage/perm_sudo_add.html', locals(), request)


@require_role('admin')
@user_operator_record
def perm_sudo_edit(request, res, *args):
    """
    list sudo commands alias
    :param request:
    :return:
    """
    # 渲染数据
    header_title, path1, path2 = "Sudo命令", "别名管理", "编辑别名"
    res['operator'] = path2
    sudo_id = request.GET.get("id")
    sudo = PermSudo.objects.get(id=sudo_id)

    try:
        if request.method == "POST":
            name = request.POST.get("sudo_name").upper()
            commands = request.POST.get("sudo_commands")
            comment = request.POST.get("sudo_comment")

            if not name or not commands:
                raise ServerError(u"sudo name 和 commands是必填项!")

            pattern = re.compile(r'[\n,\r]')
            deal_space_commands = list_drop_str(pattern.split(commands), u'')
            deal_all_commands = map(trans_all, deal_space_commands)
            commands = ', '.join(deal_all_commands).strip()
            logger.debug(u'添加sudo %s: %s' % (name, commands))
            # 更新proxy上的数据
            data = {'name': name.strip(),
                    'comment': comment,
                    'commands': commands}
            data = json.dumps(data)
            message = save_or_delete('PermSudo', data, sudo_id, 'update')
            if message == 'success':
                msg = u"添加Sudo命令别名: %s成功" % sudo.name
                res['content'] = msg
                sudo.name = name.strip()
                sudo.commands = commands
                sudo.comment = comment
                sudo.save()
            else:
                msg = u"添加Sudo命令别名: %s失败" % sudo.name
                res['flag'] = 'false'
                res['content'] = msg
    except ServerError, e:
        error = e
        res['flag'] = 'false'
        res['content'] = e
    return my_render('permManage/perm_sudo_edit.html', locals(), request)


@require_role('admin')
@user_operator_record
def perm_sudo_delete(request, res, *args):
    """
    list sudo commands alias
    :param request:
    :return:
    """
    res['operator'] = '删除别名'
    if request.method == "POST":
        # 获取参数删除的role对象
        sudo_id = request.POST.get("id")
        sudo = PermSudo.objects.get(id=sudo_id)
        # 数据库里删除记录
        message = save_or_delete('PermSudo',{}, obj_id=sudo_id, action='delete')
        if message == 'success':
            res['content'] = u'删除Sudo别名[%s]成功'% sudo.name
            sudo.delete()
        else:
            res['flag'] = 'false'
            res['content'] = u'删除Sudo别名[%s]失败'% sudo.name

        res['content'] = '删除Sudo别名[%s]' % sudo.name
        return HttpResponse(u"删除Sudo别名: %s" % sudo.name)
    else:
        res['flag'] = 'false'
        res['content'] = '不支持该操作'
        return HttpResponse(u"不支持该操作")


@require_role('admin')
def perm_role_recycle(request):
    role_id = request.GET.get('role_id')
    asset_ids = request.GET.get('asset_id').split(',')

    # 仅有推送的角色才回收
    assets = [get_object(Asset, id=asset_id) for asset_id in asset_ids]
    recycle_assets = []
    for asset in assets:
        if True in [push.success for push in asset.perm_push.all()]:
            recycle_assets.append(asset)
    recycle_resource = gen_resource(recycle_assets)
    task = MyTask(recycle_resource)
    try:
        msg_del_user = task.del_user(get_object(PermRole, id=role_id).name)
        msg_del_sudo = task.del_user_sudo(get_object(PermRole, id=role_id).name)
        logger.info("recycle user msg: %s" % msg_del_user)
        logger.info("recycle sudo msg: %s" % msg_del_sudo)
    except Exception, e:
        logger.warning("Recycle Role failed: %s" % e)
        raise ServerError(u"回收已推送的系统用户失败: %s" % e)

    for asset_id in asset_ids:
        asset = get_object(Asset, id=asset_id)
        assets.append(asset)
        role = get_object(PermRole, id=role_id)
        PermPush.objects.filter(asset=asset, role=role).delete()

    return HttpResponse('删除成功')


@require_role('user')
def perm_role_get(request):
    response = {'role_id': '', 'proxy_url': '', 'user_id': request.user.id, 'role_name': '', 'id_unique': ''}
    asset_id = request.GET.get('id', 0)
    if asset_id:
        asset = get_object(Asset, id=asset_id)
        if asset:
            role = user_have_perm(request.user, asset=asset)
            logger.debug(u'获取授权系统用户: ' + ','.join([i.name for i in role]))
            response['role_name'] = ','.join([i.name for i in role])
            response['role_id'] = ','.join(str(i.id) for i in role)
            response['proxy_url'] = asset.proxy.url
            response['id_unique'] = asset.id_unique
            return HttpResponse(json.dumps(response))
    return HttpResponse('error')

