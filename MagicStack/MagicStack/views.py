# -*- coding:utf-8 -*-

from __future__ import division
import uuid
import urllib

from django.db.models import Count
from django.shortcuts import render_to_response
from django.template import RequestContext

from django.http import HttpResponse

from MagicStack.api import *
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from logManage.models import Log, FileLog
from permManage.perm_api import get_group_user_perm, gen_resource, user_have_perm
from assetManage.models import Asset, IDC
from permManage.models import PermRole


def getDaysByNum(num):
    """
    输出格式:([datetime.date(2015, 11, 6),  datetime.date(2015, 11, 8)], ['11-06', '11-08'])
    """

    today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    date_li, date_str = [], []
    for i in range(0, num):
        today = today - oneday
        date_li.append(today)
        date_str.append(str(today)[5:10])
    date_li.reverse()
    date_str.reverse()
    return date_li, date_str


def get_data_by_day(date_li, item):
    data_li = []
    for d in date_li:
        logs = Log.objects.filter(start_time__year=d.year,
                                  start_time__month=d.month,
                                  start_time__day=d.day)
        if item == 'user':
            data_li.append(set([log.user for log in logs]))
        elif item == 'asset':
            data_li.append(set([log.host for log in logs]))
        elif item == 'login':
            data_li.append(logs)
        else:
            pass
    return data_li


def get_count_by_day(date_li, item):
    data_li = get_data_by_day(date_li, item)
    data_count_li = []
    for data in data_li:
        data_count_li.append(len(data))
    return data_count_li


def get_count_by_date(date_li, item):
    data_li = get_data_by_day(date_li, item)
    data_count_tmp = []
    for data in data_li:
        data_count_tmp.extend(list(data))

    return len(set(data_count_tmp))


@require_role(role='user')
def index_cu(request):
    username = request.user.username
    return HttpResponseRedirect(reverse('user_detail'))


@require_role(role='user')
def index(request):
    li_date, li_str = getDaysByNum(7)
    today = datetime.datetime.now().day
    from_week = datetime.datetime.now() - datetime.timedelta(days=7)

    if is_role_request(request, 'user'):
        return index_cu(request)

    elif is_role_request(request, 'super'):
        # dashboard 显示汇总
        users = User.objects.all()
        hosts = Asset.objects.all()
        online = Log.objects.filter(is_finished=0)
        online_host = online.values('host').distinct()
        online_user = online.values('user').distinct()
        active_users = User.objects.filter(is_active=1)
        active_hosts = Asset.objects.filter(is_active=1)

        # 一个月历史汇总
        date_li, date_str = getDaysByNum(30)
        date_month = repr(date_str)
        active_user_per_month = str(get_count_by_day(date_li, 'user'))
        active_asset_per_month = str(get_count_by_day(date_li, 'asset'))
        active_login_per_month = str(get_count_by_day(date_li, 'login'))

        # 活跃用户资产图
        active_user_month = get_count_by_date(date_li, 'user')
        disabled_user_count = len(users.filter(is_active=False))
        inactive_user_month = len(users) - active_user_month
        active_asset_month = get_count_by_date(date_li, 'asset')
        disabled_asset_count = len(hosts.filter(is_active=False)) if hosts.filter(is_active=False) else 0
        inactive_asset_month = len(hosts) - active_asset_month if len(hosts) > active_asset_month else 0

        # 一周top10用户和主机
        week_data = Log.objects.filter(start_time__range=(from_week, datetime.datetime.now()))
        user_top_ten = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:10]
        host_top_ten = week_data.values('host').annotate(times=Count('host')).order_by('-times')[:10]

        for user_info in user_top_ten:
            username = user_info.get('user')
            last = Log.objects.filter(user=username).latest('start_time')
            user_info['last'] = last

        for host_info in host_top_ten:
            host = host_info.get('host')
            last = Log.objects.filter(host=host).latest('start_time')
            host_info['last'] = last

        # 一周top5
        week_users = week_data.values('user').distinct().count()
        week_hosts = week_data.count()

        user_top_five = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:5]
        color = ['label-success', 'label-info', 'label-primary', 'label-default', 'label-warnning']

        # 最后10次登陆
        login_10 = Log.objects.order_by('-start_time')[:10]
        login_more_10 = Log.objects.order_by('-start_time')[10:21]

    return render_to_response('index.html', locals(), context_instance=RequestContext(request))


def is_latest():
    node = uuid.getnode()
    jsn = uuid.UUID(int=node).hex[-12:]
    with open(os.path.join(BASE_DIR, 'version')) as f:
        current_version = f.read()
    lastest_version = urllib.urlopen('http://www.jumpserver.org/lastest_version.html?jsn=%s' % jsn).read().strip()

    if current_version != lastest_version:
        pass


@defend_attack
def Login(request):
    """登录界面"""
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('index'))
    if request.method == 'GET':
        return render_to_response('login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    login(request, user)
                    if user.role == 'SU':
                        request.session['role_id'] = 2
                    elif user.role == 'GA':
                        request.session['role_id'] = 1
                    else:
                        request.session['role_id'] = 0
                    return HttpResponseRedirect(request.session.get('pre_url', '/'))
                else:
                    error = '用户未激活'
            else:
                error = '用户名或密码错误'
        else:
            error = '用户名或密码错误'
    return render_to_response('login.html', {'error': error})


@require_role('user')
def Logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))


@require_role('user')
def Help(request):
    # todo
    return render_to_response('help/ansible/index.html')

# @login_required(login_url='/login')
# def upload(request):
#     user = request.user
#     assets = get_group_user_perm(user).get('asset').keys()
#     asset_select = []
#     if request.method == 'POST':
#         remote_ip = request.META.get('REMOTE_ADDR')
#         asset_ids = request.POST.getlist('asset_ids', '')
#         upload_files = request.FILES.getlist('file[]', None)
#         date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#         upload_dir = get_tmp_dir()
#         for asset_id in asset_ids:
#             asset_select.append(get_object(Asset, id=asset_id))
#
#         if not set(asset_select).issubset(set(assets)):
#             illegal_asset = set(asset_select).issubset(set(assets))
#             return HttpResponse('没有权限的服务器 %s' % ','.join([asset.name for asset in illegal_asset]))
#
#         for upload_file in upload_files:
#             file_path = '%s/%s' % (upload_dir, upload_file.name)
#             with open(file_path, 'w') as f:
#                 for chunk in upload_file.chunks():
#                     f.write(chunk)
#
#         res = gen_resource({'user': user, 'asset': asset_select})
#         runner = MyRunner(res)
#         runner.run('copy', module_args='src=%s dest=%s directory_mode'
#                                         % (upload_dir, '/tmp'), pattern='*')
#         ret = runner.results
#         logger.debug(ret)
#         FileLog(user=request.user.username, host=' '.join([asset.name for asset in asset_select]),
#                 filename=' '.join([f.name for f in upload_files]), type='upload', remote_ip=remote_ip,
#                 result=ret).save()
#         if ret.get('failed'):
#             error = u'上传目录: %s <br> 上传失败: [ %s ] <br>上传成功 [ %s ]' % (upload_dir,
#                                                                                ','.join(ret.get('failed').keys()),
#                                                                                 ','.join(ret.get('ok').keys()))
#             return HttpResponse(error, status=500)
#         msg = u'上传目录: %s <br> 传送成功 [ %s ]' % (upload_dir, ', '.join(ret.get('ok').keys()))
#         return HttpResponse(msg)
#     return my_render('upload.html', locals(), request)


# @login_required(login_url='/login')
# def download(request):
#     user = request.user
#     assets = get_group_user_perm(user).get('asset').keys()
#     asset_select = []
#     if request.method == 'POST':
#         remote_ip = request.META.get('REMOTE_ADDR')
#         asset_ids = request.POST.getlist('asset_ids', '')
#         file_path = request.POST.get('file_path')
#         date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#         upload_dir = get_tmp_dir()
#         for asset_id in asset_ids:
#             asset_select.append(get_object(Asset, id=asset_id))
#
#         if not set(asset_select).issubset(set(assets)):
#             illegal_asset = set(asset_select).issubset(set(assets))
#             return HttpResponse(u'没有权限的服务器 %s' % ','.join([asset.name for asset in illegal_asset]))
#
#         res = gen_resource({'user': user, 'asset': asset_select})
#         runner = MyRunner(res)
#         runner.run('fetch', module_args='src=%s dest=%s' % (file_path, upload_dir), pattern='*')
#         FileLog(user=request.user.username, host=' '.join([asset.name for asset in asset_select]),
#                 filename=file_path, type='download', remote_ip=remote_ip, result=runner.results).save()
#         logger.debug(runner.results)
#         os.chdir('/tmp')
#         tmp_dir_name = os.path.basename(upload_dir)
#         tar_file = '%s.tar.gz' % upload_dir
#         bash('tar czf %s %s' % (tar_file, tmp_dir_name))
#         f = open(tar_file)
#         data = f.read()
#         f.close()
#         response = HttpResponse(data, content_type='application/octet-stream')
#         response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(tar_file)
#         return response
#
#     return render_to_response('download.html', locals(), context_instance=RequestContext(request))


@require_role('user')
def web_terminal(request):
    user = request.user
    asset_id = request.GET.get('id')
    role_id = request.GET.get('role_id')
    logger.debug('web_terminal:%s' % role_id)
    role = PermRole.objects.get(id=int(role_id))
    role_name = role.name
    asset = get_object(Asset, id_unique=asset_id)
    if asset:
        hostname = asset.name
    return render_to_response('logManage/web_terminal.html', locals())


