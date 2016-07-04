 # -*- coding:utf-8 -*-
import time
from django.db.models import Q
from userManage.user_api import *
from permManage.perm_api import get_group_user_perm
from emergency.emer_api import send_email
from emergency.models import EmergencyType

default_email = ''
if EmergencyType.objects.filter(type='0'):
    default_email = EmergencyType.objects.filter(type='0')[0]

@require_role(role='super')
@user_operator_record
def group_add(request,res, *args):
    """
    group add view for route
    添加用户组的视图
    """
    response={'success':False,'error':''}
    res['operator'] = u'添加用户组'
    res['emer_content'] = 1

    if request.method == 'POST':
        group_name = request.POST.get('name', '')
        users_selected = request.POST.getlist('select_multi', '')
        comment = request.POST.get('comment', '')
        try:
            if not group_name:
                raise ServerError(u'组名 不能为空')

            group_test = get_object(UserGroup, name = group_name)
            if group_test:
                raise ServerError(u'用户组已存在')

            db_add_group(name=group_name, users_id=users_selected, comment=comment)
        except Exception as e:
            res['flag'] = 'false'
            res['content'] = e
            res['emer_status'] = u"添加用户组[{0}]失败:{1}".format(group_name,e.message)
            response['error']=res['emer_status']
        else:
            res['content'] = u'添加用户组 %s ' % group_name
            res['emer_status'] = u"添加用户组[%s]成功"% group_name
            response['success'] = True
        return HttpResponse(json.dumps(response), content_type='application/json')
    # return my_render('userManage/group_add.html', locals(), request)


@require_role(role='super')
def group_list(request):
    """
    list user group
    用户组列表
    """
    header_title, path1, path2 = u'查看用户组', u'用户管理', u'查看用户组'
    user_group_list = UserGroup.objects.all().order_by('name')
    user_all = User.objects.all()
    return my_render('userManage/group_list.html', locals(), request)


@require_role(role='super')
@user_operator_record
def group_del(request,res, *args):
    """
    del a group
    删除用户组
    """
    res['operator'] = u'删除用户组'
    res['content'] = u'删除用户组'
    res['emer_content'] = 1
    group_ids = request.POST.get('id', '')
    group_id_list = group_ids.split(',')
    if group_id_list:
        try:
            for group_id in group_id_list:
                group = UserGroup.objects.get(id=group_id)
                res['content'] += "%s   "% group.name
                group.delete()
            msg = res['content'] + u'成功'
            res['emer_status'] = msg
        except Exception as e:
            msg = e
            res['emer_status'] = u"删除用户组失败:{0}".format(e)
    else:
        msg = u"删除用户组失败:ID不存在!"
        res['emer_status'] = msg
    return HttpResponse(msg)


@require_role(role='super')
@user_operator_record
def group_edit(request, res, *args):

    res['operator'] = u'编辑用户组'
    res['emer_content'] = 1
    if request.method == 'GET':
        group_id = request.GET.get('id', '')
        user_group = get_object(UserGroup, id=group_id)
        users_selected = User.objects.filter(group=user_group)
        users_all = User.objects.all()
        rest = dict()
        rest["Id"] = user_group.id
        rest["name"] = user_group.name
        rest["comment"] = user_group.comment
        rest["user_group"] = ','.join([str(item.id) for item in users_selected])
        return HttpResponse(json.dumps(rest), content_type='application/json')
    elif request.method == 'POST':
        response = {'success': False, 'error': ''}
        group_id = request.GET.get('id', '')
        group_name = request.POST.get('name', '')
        comment = request.POST.get('comment', '')
        users_selected = request.POST.getlist('select_multi')
        user_group = get_object(UserGroup, id=group_id)
        group_name_old = user_group.name
        try:
            if '' in [group_id, group_name]:
                raise ServerError(u'组名不能为空')

            if len(UserGroup.objects.filter(name=group_name)) > 1:
                raise ServerError(u'%s 用户组已存在' % group_name)

            user_group.user_set.clear()

            for user in User.objects.filter(id__in=users_selected):
                user.group.add(UserGroup.objects.get(id=group_id))

            user_group.name = group_name
            user_group.comment = comment
            user_group.save()

            res['content'] = u'编辑用户组%s' % group_name
            res['emer_status'] = u"编辑用户组[{0}]成功!".format(group_name_old)
            response['success'] = True
        except ServerError as e:
            error = e
            res['flag'] = 'false'
            res['comment'] = e
            res['emer_status'] = u"编辑用户组[{0}]失败:{1}".format(group_name_old, error)
            response['error'] = res['emer_status']

        return HttpResponse(json.dumps(response), content_type='application/json')


@require_role(role='super')
@user_operator_record
def user_add(request, res, *args):
    # TODO 返回页面信息
    response = {'success': False, 'error': ''}
    # TODO 用户操作记录
    res['operator'] = u'添加用户'
    # TODO 告警事件记录
    res['emer_content'] = 1

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        groups = request.POST.getlist('groups', [])
        admin_groups = request.POST.getlist('admin_groups', [])
        role = request.POST.get('role', 'CU')
        extra = request.POST.getlist('extra', [])
        is_active = False if '0' in extra else True
        send_mail_need = True if '1' in extra else False

        try:
            if '' in [username, password, name, role]:
                raise ServerError(u'带*内容不能为空')
            check_user_is_exist = User.objects.filter(username=username)
            if check_user_is_exist:
                raise ServerError(u'用户 %s 已存在' % username)
        except ServerError as e:
                res['flag'] = 'false'
                res['content'] = e.message
                res['emer_status'] = u"添加用户[{0}]失败:{1}".format(username, e.message)
                response['error'] = res['emer_status']
        else:
            try:
                user = db_add_user(username=username, name=name,
                                   password=password,
                                   email=email, role=role,
                                   groups=groups, admin_groups=admin_groups,
                                   is_active=is_active,
                                   date_joined=datetime.datetime.now())
            except IndexError, e:
                error = u'添加用户 %s 失败 %s ' % (username, e)
                res['flag'] = 'false'
                res['content'] = error
                res['emer_status'] = u"添加用户[{0}]失败:{1}".format(username, e)
                response['error'] = res['emer_status']
                db_del_user(username)
            else:
                if send_mail_need:
                    if not default_email:
                        error = u"没有邮件服务器信息,请先到告警管理配置邮件服务器,谢谢!"
                        return HttpResponse(error)
                    user_add_mail(user, default_email, kwargs=locals())
                res['content'] = u'添加用户 %s' % username
                res['emer_status'] = u"添加用户[{0}]成功".format(username)
                response['success'] = True
                response['error'] = res['emer_status']
    return HttpResponse(json.dumps(response), content_type='application/json')


@require_role(role='super')
def user_list(request):
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    header_title, path1, path2 = u'查看用户', u'用户管理', u'用户列表'
    users_list = User.objects.all().order_by('username')
    group_all = UserGroup.objects.all()
    user_role = {'SU': u'超级管理员', 'CU': u'普通用户'}
    return my_render('userManage/user_list.html', locals(), request)


@require_role(role='user')
def user_detail(request):
    header_title, path1, path2 = u'用户详情', u'用户管理', u'用户详情'
    if request.session.get('role_id') == 0:
        user_id = request.user.id
    else:
        user_id = request.GET.get('id', '')

    user = get_object(User, id=user_id)
    if not user:
        return HttpResponseRedirect(reverse('user_list'))

    user_perm_info = get_group_user_perm(user)
    role_assets = user_perm_info.get('role')
    user_log_ten = Log.objects.filter(user=user.username).order_by('id')[0:10]
    user_log_last = Log.objects.filter(user=user.username).order_by('id')[0:50]
    user_log_last_num = len(user_log_last)

    return my_render('userManage/user_detail.html', locals(), request)


@require_role(role='admin')
@user_operator_record
def user_del(request, res, *args):
    res['operator'] = u'删除用户'
    user_ids = request.POST.get('id', '')
    user_id_list = user_ids.split(',')
    res['content'] = u'删除用户'
    res['emer_content'] = 1
    for user_id in user_id_list:
        try:
            user = get_object(User, id=user_id)
            if user and user.username != 'admin':
                res['content'] += "%s   "%user.username
                user.delete()
            msg = res['content'] + u"成功"
            res['emer_status'] = msg
        except Exception, e:
            res['flag'] = 'false'
            res['content'] = e
            msg = u"删除用户失败:{0}".format(e)
    return HttpResponse(msg)


@require_role('admin')
@user_operator_record
def send_mail_retry(request,res, *args):
    res['operator'] = u'发送邮件'
    uuid_r = request.GET.get('uuid', '1')
    user = get_object(User, uuid=uuid_r)
    msg = u"""
    MagicStack地址： %s
    用户名：%s
    重设密码：%s/userManage/password/forget/
    请登录web点击个人信息页面重新生成ssh密钥
    """ % (URL, user.username, URL)
    if not default_email:
        return HttpResponse(u'没有邮件服务器信息,请先到告警管理中配置邮件服务器,谢谢!')
    try:
        send_email(default_email, u'邮件重发', [user.email], msg)
    except IndexError,e:
        res['flag'] = 'false'
        res['comment'].append(e)
        return Http404

    res['comment'] = u'发送邮件成功'
    return HttpResponse(u'发送成功')


@defend_attack
def forget_password(request):
    if request.method == 'POST':
        defend_attack(request)
        email = request.POST.get('email', '')
        username = request.POST.get('username', '')
        user = get_object(User, username=username, email=email)
        if user:
            timestamp = int(time.time())
            hash_encode = PyCrypt.md5_crypt(str(user.uuid) + str(timestamp) + KEY)
            msg = u"""
            Hi %s, 请点击下面链接重设密码！
            %s/userManage/password/reset/?uuid=%s&timestamp=%s&hash=%s
            """ % (user.name, URL, user.uuid, timestamp, hash_encode)
            if not default_email:
                error = u'没有邮件服务器信息,请先到告警管理中配置邮件服务器,谢谢!'
            send_email(default_email, u'忘记登录密码', [email], msg)
            msg = u'请登陆邮箱，点击邮件重设密码'
            return http_success(request, msg)
        else:
            error = u'用户不存在或邮件地址错误'
            return http_error(request, error)


@defend_attack
def reset_password(request):
    uuid_r = request.GET.get('uuid', '')
    timestamp = request.GET.get('timestamp', '')
    hash_encode = request.GET.get('hash', '')
    action = '/userManage/password/reset/?uuid=%s&timestamp=%s&hash=%s' % (uuid_r, timestamp, hash_encode)

    if hash_encode == PyCrypt.md5_crypt(uuid_r + timestamp + KEY):
        if int(time.time()) - int(timestamp) > 600:
            return http_error(request, u'链接已超时')
    else:
        return HttpResponse('hash校验失败')

    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        print password, password_confirm
        if password != password_confirm:
            return HttpResponse(u'密码不匹配')
        else:
            user = get_object(User, uuid=uuid_r)
            if user:
                user.password = PyCrypt.md5_crypt(password)
                user.save()
                return http_success(request, u'密码重设成功')
            else:
                return HttpResponse(u'用户不存在')

    elif request.method == 'GET':
        return render_to_response('userManage/reset_password.html', locals())
    else:
        return http_error(request, u'错误请求')


@require_role(role='super')
@user_operator_record
def user_edit(request,res, *args):
    res['operator'] = u'编辑用户'
    res['emer_content'] = 1
    if request.method == 'GET':
        rest = {}
        user_id = request.GET.get('id', '')
        if not user_id:
            return HttpResponseRedirect(reverse('index'))
        user = get_object(User, id=user_id)
        if user:
            groups_str = ','.join([str(group.id) for group in user.group.all()])
            admin_groups_str = ' '.join([str(admin_group.group.id) for admin_group in user.admingroup_set.all()])
            is_super = True if user.role == 'SU' else False
            rest['Id'] = user.id
            rest['username'] = user.username
            rest['name'] = user.name
            rest['password'] = user.password
            rest['email'] = user.email
            rest['is_active'] = user.is_active
            rest['user_group'] = groups_str
            rest['is_super'] = is_super
            return HttpResponse(json.dumps(rest), content_type='application/json')
    else:
        response = {'success': False, 'error': ''}
        try:
            user_id = request.GET.get('id', '')
            password = request.POST.get('password', '')
            name = request.POST.get('name', '')
            email = request.POST.get('email', '')
            groups = request.POST.getlist('groups', [])
            role_post = request.POST.get('role', 'CU')
            admin_groups = request.POST.getlist('admin_groups', [])
            extra = request.POST.getlist('extra', [])
            is_active = False if '0' in extra else True
            email_need = True if '1' in extra else False
            user_role = {'SU': u'超级管理员', 'GA': u'部门管理员', 'CU': u'普通用户'}

            if user_id:
                user = get_object(User, id=user_id)
                username_old = user.username
            else:
                res['flag'] = 'false'
                res['content'] = u'用户不存在!'
                res['emer_satus'] = u"编辑用户失败:{1}".format(u'用户不存在!')
                response['error'] = u"编辑用户失败:{1}".format(u'用户不存在!')

            db_update_user(user_id=user_id,
                           password=password,
                           name=name,
                           email=email,
                           groups=groups,
                           admin_groups=admin_groups,
                           role=role_post,
                           is_active=is_active)

            res['content'] = u'编辑用户%s' % user.username
            res['emer_status'] = u"编辑用户[{0}]成功".format(username_old)
            response['success'] = True
            response['error'] = res['emer_status']
            if email_need:
                emsg = u"""
                Hi %s:
                    您的信息已修改，请登录MagicStack查看详细信息
                    地址：%s
                    用户名： %s
                    密码：%s (如果密码为None代表密码为原密码)
                    权限：：%s

                """ % (user.name, URL, user.username, password, user_role.get(role_post, u''))

                if not default_email:
                    error = u"没有邮件服务器信息,请先到告警管理配置邮件服务器,谢谢!"
                    return HttpResponse(error)
                send_email(default_email, u'您的信息已修改',[email], emsg)
        except Exception as e:
            logger.error(e)
            res['flag'] = 'false'
            error_info = u"编辑用户失败:{0}".format(e.message)
            res['content'] = res['emer_status'] = response['error'] = error_info
        return HttpResponse(json.dumps(response), content_type='application/json')


@require_role('user')
def profile(request):
    user_id = request.user.id
    if not user_id:
        return HttpResponseRedirect(reverse('index'))
    user = User.objects.get(id=user_id)
    return my_render('userManage/profile.html', locals(), request)


def change_info(request):
    header_title, path1, path2 = u'修改信息', u'用户管理', u'修改个人信息'
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    error = ''
    if not user:
        return HttpResponseRedirect(reverse('index'))

    if request.method == 'POST':
        name = request.POST.get('name', '')
        password = request.POST.get('password', '')
        email = request.POST.get('email', '')

        if '' in [name, email]:
            error = u'不能为空'

        if not error:
            User.objects.filter(id=user_id).update(name=name, email=email)
            if len(password) > 0:
                user.set_password(password)
                user.save()
            msg = u'修改成功'

    return my_render('userManage/change_info.html', locals(), request)


@require_role(role='user')
def regen_ssh_key(request):
    uuid_r = request.GET.get('uuid', '')
    user = get_object(User, uuid=uuid_r)
    if not user:
        return HttpResponse(u'没有该用户')

    username = user.username
    ssh_key_pass = PyCrypt.gen_rand_pass(16)
    gen_ssh_key(username, ssh_key_pass)
    return HttpResponse(u'ssh密钥已生成，密码为 %s, 请到下载页面下载' % ssh_key_pass)


@require_role(role='user')
def down_key(request):
    if is_role_request(request, 'super'):
        uuid_r = request.GET.get('uuid', '')
    else:
        uuid_r = request.user.uuid
    if uuid_r:
        user = get_object(User, uuid=uuid_r)
        if user:
            username = user.username
            private_key_file = os.path.join(KEY_DIR, 'user', username+'.pem')
            if os.path.isfile(private_key_file):
                f = open(private_key_file)
                data = f.read()
                f.close()
                response = HttpResponse(data, content_type='application/octet-stream')
                response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(private_key_file)
                if request.user.role == 'CU':
                    os.unlink(private_key_file)
                return response
    return HttpResponse('No Key File. Contact Admin.')

