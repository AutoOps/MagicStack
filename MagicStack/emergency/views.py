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
from django.shortcuts import HttpResponseRedirect, HttpResponse
import json
from MagicStack.api import  my_render, require_role, CRYPTOR, ServerError, logger
from userManage.user_api import user_operator_record
from emergency.models import *
from emergency.emer_api import send_email

MEDIA_TYPES = {'0': u'电子邮件', '1': u'微信', '2':u'短信'}
EMER_CONTENTS = {
        '1': u'用户变更',
        '2': u'资产变更',
        '3': u'应用变更',
        '4': u'任务变更',
        '5': u'备份变更',
        '6': u'授权变更',
        '7': u'代理变更'
    }


@require_role('user')
def media_list(request):
    if request.method == "GET":
        header_title, path1, path2 = u'告警媒介类型', u'告警管理', u'查看告警媒介类型'
        return my_render('emergency/media_list.html', locals(), request)
    else:
        try:
            page_length = int(request.POST.get('length', '5'))
            total_length = EmergencyType.objects.all().count()
            keyword = request.POST.get("search")
            rest = {
                "iTotalRecords": 0,   # 本次加载记录数量
                "iTotalDisplayRecords": total_length,  # 总记录数量
                "aaData": []}
            page_start = int(request.POST.get('start', '0'))
            page_end = page_start + page_length
            page_data = EmergencyType.objects.all()[page_start:page_end]
            rest['iTotalRecords'] = len(page_data)
            data = []
            for item in page_data:
                res={}
                res['id']=item.id
                res['name']=item.name
                res['type']= u'电子邮件'if '0' in item.type else u'微信'
                res['status']= u'启用'if '1'in item.status else u'禁用'
                res['detail']=item.detail
                res['comment']=item.comment
                data.append(res)
            rest['aaData']=data
            return HttpResponse(json.dumps(rest), content_type='application/json')
        except Exception as e:
            logger.error(e.message)


@require_role('admin')
@user_operator_record
def media_add(request, res, *args):
    response = {'success': False, 'error': ''}
    res['operator'] = u'添加告警媒介'
    if request.method == 'POST':
        try:
            media_name = request.POST.get('media_name', '')
            if EmergencyType.objects.filter(name=media_name):
                    raise ServerError(u'名称[%s]已存在'%media_name)
            media_type = request.POST.get('media_type', '')
            if media_type == '0':
                smtp_host = request.POST.get('smtp_host', '')
                smtp_host_port = request.POST.get('smtp_host_port', 587)
                email_user = request.POST.get('email_user', '')
                email_user_password = request.POST.get('email_user_password', '')
                encrypt_password = CRYPTOR.encrypt(email_user_password)
                connect_security = request.POST.getlist('connection', [])
                status = request.POST.get('extra', '0')
                comment = request.POST.get('comment', '')
                is_use_tls = True if '1' in connect_security else 0
                is_use_ssl = True if '0' in connect_security else 0
                media_detail = u"SMTP服务器:{0}    SMTP电邮:{1}".format(smtp_host, email_user)

                if '' in [media_name, smtp_host, smtp_host_port, email_user, email_user_password]:
                    raise ServerError(u'必要参数不能为空,请从新填写')

                EmergencyType.objects.create(name=media_name, type=media_type, smtp_server=smtp_host, smtp_server_port=int(smtp_host_port),
                                             status=status, email_username=email_user, email_password=encrypt_password,
                                             email_use_ssl=is_use_ssl, email_use_tls=is_use_tls,detail=media_detail, comment=comment)

                res['content'] = u'添加告警媒介[%s]成功' % media_name
                response['success'] = True
                response['error'] = u'添加告警媒介[%s]成功' % media_name
            elif media_type == '1':
                corpid = request.POST.get('corpid', '')
                corpsecret = request.POST.get('corpsecret', '')
                status = request.POST.get('extra', '0')
                comment = request.POST.get('comment', '')

                if '' in [media_name, corpid, corpsecret]:
                    raise ServerError(u'必要参数为空,请从新填写!')

                media_detail = u'CorpID:%s '%corpid
                EmergencyType.objects.create(name=media_name, type=media_type, corpid=corpid, corpsecret=corpsecret,
                                             detail=media_detail, status=status, comment=comment)
                res['content'] = u'添加成功'
                response['success'] = True
                response['error'] = u'添加成功'
        except Exception as e:
            res['flag'] = False
            res['content'] = e.message
            response['error'] = u'添加media失败：%s'%e.message
    return HttpResponse(json.dumps(response), content_type='application/json')


@require_role('user')
@user_operator_record
def media_edit(request, res):
    res['operator'] = u'编辑告警媒介'
    if request.method == 'GET':
        try:
            media_id = request.GET.get('id', '')
            media_info = EmergencyType.objects.get(id=int(media_id))
            rest = {}
            rest['Id'] = media_info.id
            rest['name'] = media_info.name
            rest['type'] = media_info.type
            rest['status'] = media_info.status
            rest['smtp_server'] = media_info.smtp_server
            rest['smtp_server_port'] = media_info.smtp_server_port
            rest['email_username'] = media_info.email_username
            email_psswd = CRYPTOR.decrypt(media_info.email_password) if media_info.email_password else ''  # 将密码解密后在传到前端
            rest['email_password'] = email_psswd
            rest['email_use_tls'] = media_info.email_use_tls
            rest['email_use_ssl'] = media_info.email_use_ssl
            rest['corpid'] = media_info.corpid
            rest['corpsecret'] = media_info.corpsecret
            rest['comment'] = media_info.comment
            return HttpResponse(json.dumps(rest), content_type='application/json')
        except Exception as e:
            logger.error(e.message)
            return HttpResponse(e.message)
    else:
        response = {'success': False, 'error': ''}
        m_id = request.GET.get('id', '')
        media = EmergencyType.objects.get(id=int(m_id))
        media_name = request.POST.get('media_name', '')
        media_type = request.POST.get('media_type', '')
        try:
            old_name=media.name
            if old_name==media_name:
                if EmergencyType.objects.filter(name=media_name).count()>1:
                    raise ServerError(u'名称[%s]已存在'% media_name)
            else:
                if EmergencyType.objects.filter(name=media_name).count()>0:
                    raise ServerError(u"名称[%s]已存在"% media_name)
            if media_type == '0':
                smtp_host = request.POST.get('smtp_host', '')
                smtp_host_port = int(request.POST.get('smtp_host_port', 587))
                email_user = request.POST.get('email_user', '')
                email_user_password = request.POST.get('email_user_password', '')
                encrypt_password = CRYPTOR.encrypt(email_user_password)
                connect_security = request.POST.getlist('connection', [])
                status = request.POST.get('extra', '0')
                comment = request.POST.get('comment', '')
                is_use_tls = True if '1' in connect_security else 0
                is_use_ssl = True if '0' in connect_security else 0
                media_detail = u"SMTP服务器:{0}    SMTP电邮:{1}".format(smtp_host, email_user)

                if '' in [media_name, smtp_host, smtp_host_port, email_user, email_user_password]:
                    raise ServerError(u'名称不能为空')

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

                res['content'] = u'修改告警媒介[%s]成功' % media_name
                response['success'] = True
            elif media_type == '1':

                corpid = request.POST.get('corpid', '')
                corpsecret = request.POST.get('corpsecret', '')
                status = request.POST.get('extra', '0')
                comment = request.POST.get('comment', '')
                media_detail = u'CorpID:%s'%corpid
                if '' in [media_name, corpid, corpsecret]:
                    raise ServerError(u'必要参数为空,请从新填写!')

                media.name = media_name
                media.type = media_type
                media.status = status
                media.corpid = corpid
                media.detail = media_detail
                media.corpsecret = corpsecret
                media.comment = comment
                media.save()
                res['content'] = u'修改告警媒介[%s]成功'%media.name
                response['success'] = True
        except Exception as e:
            logger.error(e)
            res['flag'] = 'false'
            response['error'] =res['content'] = u'修改告警媒介失败：%s'%e.message
        return HttpResponse(json.dumps(response), content_type='application/json')


@require_role('user')
@user_operator_record
def media_del(request, res):
    res['operator'] = u'删除告警媒介类型'
    res['content'] = u'删除告警媒介类型'
    selected_id = request.GET.get('id')
    media_ids = selected_id.split(',')
    if media_ids:
        try:
            for item in media_ids:
                media = EmergencyType.objects.get(id=int(item))
                res['content'] += u' [%s]  ' % media.name
                media.delete()
            msg = res['content'] + u"成功"
            res['emer_status']=msg
        except Exception as e:
            res['flag'] = 'flase'
            res['content']=e.message
            msg = u"删除告警媒介失败：%s"%e.message
    return HttpResponse(msg)


@require_role('admin')
def emergency_rule(request):
    if request.method == 'GET':
        header_title, path1, path2 = u"告警规则设置", u"告警管理", u"告警规则"
        users = User.objects.all()
        media_list = EmergencyType.objects.all()
        return my_render('emergency/emer_rules.html', locals(), request)
    else:
        try:
            page_length = int(request.POST.get('length', '5'))
            total_length = EmergencyRules.objects.all().count()
            keyword = request.POST.get("search")
            rest = {
                "iTotalRecords": 0,   # 本次加载记录数量
                "iTotalDisplayRecords": total_length,  # 总记录数量
                "aaData": []}
            page_start = int(request.POST.get('start', '0'))
            page_end = page_start + page_length
            page_data = EmergencyRules.objects.all()[page_start:page_end]
            rest['iTotalRecords'] = len(page_data)
            data = []
            emer_content = EMER_CONTENTS
            time_types = {'1': u'全部', '2': u'工作日', '3': u'周末'}
            for item in page_data:
                res = {}
                res['id'] = item.id
                res['content'] = emer_content.get(str(item.content), '')
                res['user'] = ','.join([user.username for user in item.staff.all()])
                res['emergency_time'] = time_types.get(str(item.emergency_time), '')
                res['media_type'] = item.media_type.name if item.media_type else ''
                res['status'] = u'启用' if item.status else u'禁用'
                data.append(res)
            rest['aaData'] = data
            return HttpResponse(json.dumps(rest), content_type='application/json')
        except Exception as e:
            logger.error(e.message)



@require_role('admin')
def emergency_edit(request):
    response = {}
    emer_content = EMER_CONTENTS
    if request.method == "GET":
        emer_id = request.GET.get('id')
        if emer_id:
            emer_rule = EmergencyRules.objects.get(id=int(emer_id))
            response['emer_id'] = emer_id
            response['emer_content'] = emer_content[str(emer_rule.content)]
            response['emer_user'] = ','.join([str(user.id) for user in emer_rule.staff.all()])
            response['emer_time'] = str(emer_rule.emergency_time)
            response['media_type'] = str(emer_rule.media_type.id) if emer_rule.media_type else ''
            response['emer_status'] = str(emer_rule.status)
            response['is_add'] = emer_rule.is_add
            response['is_updated'] = emer_rule.is_update
            response['is_delete'] = emer_rule.is_delete
            return HttpResponse(json.dumps(response), content_type="application/json")
        else:
            return HttpResponse(u'Not Found')


@require_role('admin')
@user_operator_record
def emergency_save(request, res):
    response = {'success':'false', 'error': ''}
    res['operator'] = u"编辑告警规则"
    if request.method == 'POST':
        params = json.loads(request.POST.get('param', ''))
        emer_id = params.get('id')
        if emer_id:
            try:
                emer_rule = EmergencyRules.objects.get(id=int(emer_id))
                select_user = params.get('emer_user', '')
                emer_time = params.get('emer_time',1)
                media_type_id = params.get('media_type', '1')
                emer_status = params.get('emer_status',1)
                is_add = params.get('is_add', 1)
                is_update = params.get('is_update', 1)
                is_delete = params.get('is_delete', 1)

                emer_rule.staff = select_user
                emer_rule.emergency_time = emer_time
                emer_rule.media_type = EmergencyType.objects.get(id=int(media_type_id))
                emer_rule.status = emer_status
                emer_rule.is_add = is_add
                emer_rule.is_delete = is_delete
                emer_rule.is_update = is_update
                emer_rule.save()
                response['success'] = 'true'
                res['content'] = u"编辑告警规则成功"
            except Exception as e:
                response['error'] = e
                res['flag'] = 'false'
                res['content'] = e
        else:
            response['error'] = u'ID不存在'
            res['flag'] = 'false'
            res['content'] = response['error']
        return HttpResponse(json.dumps(response), content_type='application/json')


@require_role('admin')
def emergency_event(request):
    if request.method == 'GET':
        header_title, path1, path2 = u"告警事件", u'告警管理', u'告警事件'
        return my_render('emergency/emer_event.html', locals(), request)
    else:
        try:
            page_length = int(request.POST.get('length', '5'))
            total_length = EmergencyEvent.objects.all().count()
            keyword = request.POST.get("search")
            rest = {
                "iTotalRecords": 0,   # 本次加载记录数量
                "iTotalDisplayRecords": total_length,  # 总记录数量
                "aaData": []}
            page_start = int(request.POST.get('start', '0'))
            page_end = page_start + page_length
            page_data = EmergencyEvent.objects.all()[page_start:page_end]
            rest["iTotalRecords"] = len(page_data)
            data = []
            emer_content = EMER_CONTENTS
            for item in page_data:
                res = {}
                res['id'] = item.id
                res['emer_time'] = item.emer_time.strftime("%Y-%m-%d %H:%M:%S")
                res['emer_event'] = emer_content.get(str(item.emer_event.content), '')
                res['emer_user'] = item.emer_user
                res['emer_id'] = item.id
                res['emer_info'] = item.emer_info
                res['emer_result'] = u'已执行' if item.emer_result else u'未执行'
                res['emer_content_num'] = item.emer_event.content
                data.append(res)
            rest['aaData'] = data
            return HttpResponse(json.dumps(rest), content_type='application/json')
        except Exception as e:
            logger.error(e.message)




