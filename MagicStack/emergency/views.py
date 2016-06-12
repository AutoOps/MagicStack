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
from MagicStack.api import pages, my_render, require_role, CRYPTOR, ServerError, logger
from userManage.user_api import user_operator_record
from emergency.models import EmergencyType

MEDIA_TYPES = {'0': u'电子邮件', '1': u'微信', '2':u'短信'}


@require_role('user')
def media_list(request):
    header_title, path1, path2 = u'告警媒介类型', u'告警管理', u'查看告警媒介类型'
    media_lists = EmergencyType.objects.all()
    return my_render('emergency/media_list.html', locals(), request)


@require_role('admin')
@user_operator_record
def media_add(request, res, *args):
    error = msg = ''
    header_title, path1, path2 = u'添加告警媒介', u'告警管理', u'添加告警媒介'
    res['operator'] = path2
    if request.method == 'POST':
        media_name = request.POST.get('media_name', '')
        media_type = request.POST.get('media_type', '')
        if media_type == '0':
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
            media_detail = u"SMTP服务器:{0}    SMTP电邮:{1}".format(smtp_host, email_user)
            try:
                if '' in [media_name, smtp_host, smtp_host_port, email_user, email_user_password]:
                    raise ServerError(u'必要参数不能为空,请从新填写')
                if EmergencyType.objects.filter(name=media_name):
                    raise ServerError(u'名称已存在')
                EmergencyType.objects.create(name=media_name, type=media_type, smtp_server=smtp_host, smtp_server_port=smtp_host_port,
                                             status=status, email_username=email_user, email_password=encrypt_password,
                                             email_use_ssl=is_use_ssl, email_use_tls=is_use_tls,detail=media_detail, comment=comment)
                msg = u'添加告警媒介[%s]成功' % media_name
                res['content'] = msg
                return HttpResponseRedirect(reverse('media_list'))
            except ServerError, e:
                error = e
                res['flag'] = False
                res['content'] = error
        elif media_type == '1':
            corpid = request.POST.get('corpid', '')
            corpsecret = request.POST.get('corpsecret', '')
            status = request.POST.get('extra', '')
            comment = request.POST.get('comment', '')
            try:
                if '' in [media_name, corpid, corpsecret]:
                    raise ServerError(u'必要参数为空,请从新填写!')
                if EmergencyType.objects.filter(name=media_name):
                    raise ServerError(u'名称已存在')
                media_detail = u'CorpID:%s '%corpid
                EmergencyType.objects.create(name=media_name, type=media_type, corpid=corpid, corpsecret=corpsecret,
                                             detail=media_detail, status=status, comment=comment)
                res['content'] = u'添加成功'
                return HttpResponseRedirect(reverse('media_list'))
            except Exception as e:
                error = e
                res['flag'] = False
                res['content'] = error
    return my_render('emergency/media_add.html', locals(), request)


@require_role('user')
@user_operator_record
def media_edit(request, res):
    error = msg = ''
    header_title, path1, path2 = u'编辑告警媒介', u'告警管理', u'编辑告警媒介'
    res['operator'] = path2
    media_id = request.GET.get('id', '')
    media_info = EmergencyType.objects.get(id=int(media_id))
    if request.method == 'POST':
        media_name = request.POST.get('media_name', '')
        media_type = request.POST.get('media_type', '')
        if media_type == '0':
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
            media_detail = u"SMTP服务器:{0}    SMTP电邮:{1}".format(smtp_host, email_user)
            try:
                if '' in [media_name, smtp_host, smtp_host_port, email_user, email_user_password]:
                    raise ServerError(u'名称不能为空')
                if EmergencyType.objects.filter(name=media_name).count()> 1:
                    raise ServerError(u'名称已存在')
                media = EmergencyType.objects.get(id=int(media_id))
                media.name = media_name
                media.type = media_type
                media.smtp_server = smtp_host
                media.smtp_server_port = smtp_host_port
                media.status = status
                media.email_username = email_user
                media.email_password = encrypt_password
                media.email_use_ssl = is_use_ssl
                media.email_use_tls = is_use_tls
                media.detail = media_detail
                media.comment = comment
                media.save()
                msg = u'修改告警媒介[%s]成功' % media_name
                res['content'] = msg
                return HttpResponseRedirect(reverse('media_list'))
            except ServerError, e:
                error = e
                res['flag'] = False
                res['content'] = error
        elif media_type == '1':
            try:
                corpid = request.POST.get('corpid', '')
                corpsecret = request.POST.get('corpsecret', '')
                status = request.POST.get('extra', '')
                comment = request.POST.get('comment', '')
                media_detail = u'CorpID:%s'%corpid
                if '' in [media_name, corpid, corpsecret]:
                    raise ServerError(u'必要参数为空,请从新填写!')
                if EmergencyType.objects.filter(name=media_name).count() > 1:
                    raise ServerError(u'名称已存在')
                media_info.name = media_name
                media_info.type = media_type
                media_info.status = status
                media_info.corpid = corpid
                media_info.corpsecret = corpsecret
                media_info.save()
                res['content'] = u'修改告警媒介[%s]成功'%media_info.name
                return HttpResponseRedirect(reverse('media_list'))
            except Exception as e:
                logger.error(e)
                error = e
                res['flag'] = 'false'
                res['content'] = e
    return my_render('emergency/media_edit.html', locals(), request)


@require_role('user')
@user_operator_record
def media_del(request, res):
    msg = ''
    res['operator'] = u'删除告警媒介类型'
    res['content'] = u'删除告警媒介类型'
    selected_id = request.GET.get('id')
    media_ids = selected_id.split(',')
    for item in media_ids:
        media = EmergencyType.objects.get(id=int(item))
        msg += '  %s  ' % media.name
        res['content'] += u' [%s]  ' % media.name
        media.delete()
    return HttpResponse(u'删除[%s]成功' % msg)