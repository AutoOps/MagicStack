# -*- coding:utf-8 -*-
# Copyright (c) 2016 MagicStack
#
# Licensed under the Apache License, Version 2.0 (the "License");
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
from django.db.models import Q
from django.shortcuts import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from MagicStack.api import pages, my_render, require_role, CRYPTOR, ServerError
from userManage.user_api import user_operator_record
from emergency.models import EmergencyType

MEDIA_TYPES = [u'电子邮件', u'微信', u'短信']


@require_role('user')
def media_list(request):
    header_title, path1, path2 = u'告警媒介类型', u'告警管理', u'查看告警媒介类型'
    keyword = request.GET.get('search', '')
    media_lists = EmergencyType.objects.all()
    media_id = request.GET.get('id', '')

    if keyword:
        media_lists = media_lists.filter(Q(name__icontains=keyword) | Q(create_time__icontains=keyword))

    if media_id:
        media_lists = media_lists.filter(id=int(media_id))

    media_lists, p, medias, page_range, current_page, show_first, show_end = pages(media_lists, request)
    return my_render('emergency/media_list.html', locals(), request)


@require_role('admin')
@user_operator_record
def media_add(request, res, *args):
    error = msg = ''
    header_title, path1, path2 = u'添加告警媒介', u'告警管理', u'添加告警媒介'
    media_types = MEDIA_TYPES
    res['operator'] = path2
    if request.method == 'POST':
        media_name = request.POST.get('media_name', '')
        media_type = request.POST.get('media_type', '')
        smtp_host = request.POST.get('smtp_host', '')
        smtp_host_port = int(request.POST.get('smtp_host_port', 587))
        email_user = request.POST.get('email_user', '')
        email_user_password = request.POST.get('email_user_password', '')
        encrypt_password = CRYPTOR.encrypt(email_user_password)
        connect_security = request.POST.getlist('connection', [])
        status = request.POST.get('extra', '')
        comment = request.POST.get('comment', '')
        is_use_tls = True if '1' in connect_security else 0
        is_use_ssl = True if '0' in connect_security else 0
        media_status = u'启用' if status == '1' else u'禁用'
        media_detail = "SMTP服务器:{0}    SMTP电邮:{1}".format(smtp_host, email_user)
        try:
            if not media_name:
                raise ServerError('名称不能为空')
            if EmergencyType.objects.filter(name=media_name):
                raise ServerError('名称已存在')
            EmergencyType.objects.create(name=media_name, type=media_type, smtp_server=smtp_host, smtp_server_port=smtp_host_port,
                                         status=media_status, email_username=email_user, email_password=encrypt_password,
                                         email_use_ssl=is_use_ssl, email_use_tls=is_use_tls,detail=media_detail, comment=comment)
            msg = '添加告警媒介[%s]成功' % media_name
            res['content'] = msg
            return HttpResponseRedirect(reverse('media_list'))
        except ServerError, e:
            error = e
            res['flag'] = False
            res['content'] = error

    return my_render('emergency/media_add.html', locals(), request)


def media_edit(request):
    pass


@require_role('user')
@user_operator_record
def media_del(request, res):
    msg = ''
    res['operator'] = '删除代理'
    res['content'] = '删除代理'
    selected_id = request.GET.get('id')
    media_ids = selected_id.split(',')
    for item in media_ids:
        media = EmergencyType.objects.get(id=int(item))
        msg += '  %s  ' % media.name
        res['content'] += ' [%s]  ' % media.name
        media.delete()
    return HttpResponse('删除[%s]成功' % msg)