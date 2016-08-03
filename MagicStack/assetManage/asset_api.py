# coding: utf-8
from __future__ import division
import xlrd
from MagicStack.api import *
from assetManage.models import ASSET_STATUS, ASSET_TYPE, ASSET_ENV, IDC, AssetRecord, Asset, AssetGroup
from common.interface import APIRequest
from django.db.models.query import QuerySet
import traceback
import ast


def group_add_asset(group, asset_id=None, asset_ip=None):
    """
    资产组添加资产
    Asset group add a asset
    """
    if asset_id:
        asset = get_object(Asset, id=asset_id)
    else:
        asset = get_object(Asset, ip=asset_ip)

    if asset:
        group.asset_set.add(asset)


def db_add_group(**kwargs):
    """
    add a asset group in database
    数据库中添加资产
    """
    name = kwargs.get('name')
    group = get_object(AssetGroup, name=name)
    asset_id_list = kwargs.pop('asset_select')

    if not group:
        group = AssetGroup(**kwargs)
        group.save()
        for asset_id in asset_id_list:
            group_add_asset(group, asset_id)


def db_update_group(**kwargs):
    """
    add a asset group in database
    数据库中更新资产
    """
    group_id = kwargs.pop('id')
    asset_id_list = kwargs.pop('asset_select')
    group = get_object(AssetGroup, id=group_id)

    for asset_id in asset_id_list:
        group_add_asset(group, asset_id)

    AssetGroup.objects.filter(id=group_id).update(**kwargs)


def db_asset_add(**kwargs):
    """
    add asset to db
    添加主机时数据库操作函数
    """
    group_id_list = kwargs.pop('groups')
    asset = Asset(**kwargs)
    asset.save()

    group_select = []
    for group_id in group_id_list:
        group = AssetGroup.objects.filter(id=group_id)
        group_select.extend(group)
    asset.group = group_select


def db_asset_update(**kwargs):
    """ 修改主机时数据库操作函数 """
    asset_id = kwargs.pop('id')
    Asset.objects.filter(id=asset_id).update(**kwargs)


def get_tuple_name(asset_tuple, value):
    """"""
    for t in asset_tuple:
        if t[0] == value:
            return t[1]

    return ''


def get_tuple_diff(asset_tuple, field_name, value):
    """"""
    old_name = get_tuple_name(asset_tuple, int(value[0])) if value[0] else u''
    new_name = get_tuple_name(asset_tuple, int(value[1])) if value[1] else u''
    alert_info = [field_name, old_name, new_name]
    return alert_info


def db_asset_alert(asset, username, alert_dic):
    """
    asset alert info to db
    """
    alert_list = []
    asset_tuple_dic = {'status': ASSET_STATUS, 'env': ASSET_ENV, 'asset_type': ASSET_TYPE}
    for field, value in alert_dic.iteritems():
        field_name = Asset._meta.get_field_by_name(field)[0].verbose_name
        if field == 'idc':
            old = IDC.objects.filter(id=value[0]) if value[0] else u''
            new = IDC.objects.filter(id=value[1]) if value[1] else u''
            old_name = old[0].name if old else u''
            new_name = new[0].name if new else u''
            alert_info = [field_name, old_name, new_name]

        elif field in ['status', 'env', 'asset_type']:
            alert_info = get_tuple_diff(asset_tuple_dic.get(field), field_name, value)

        elif field == 'group':
            old, new = [], []
            for group_id in value[0]:
                group_name = AssetGroup.objects.get(id=int(group_id)).name
                old.append(group_name)
            for group_id in value[1]:
                group_name = AssetGroup.objects.get(id=int(group_id)).name
                new.append(group_name)
            if sorted(old) == sorted(new):
                continue
            else:
                alert_info = [field_name, ','.join(old), ','.join(new)]

        elif field == 'use_default_auth':
            if unicode(value[0]) == 'True' and unicode(value[1]) == 'on' or \
                                    unicode(value[0]) == 'False' and unicode(value[1]) == '':
                continue
            else:
                name = asset.username
                alert_info = [field_name, u'默认', name] if unicode(value[0]) == 'True' else \
                    [field_name, name, u'默认']

        elif field in ['username', 'password']:
            continue

        elif field == 'is_active':
            if unicode(value[0]) == 'True' and unicode(value[1]) == '1' or \
                                    unicode(value[0]) == 'False' and unicode(value[1]) == '0':
                continue
            else:
                alert_info = [u'是否激活', u'激活', u'禁用'] if unicode(value[0]) == 'True' else \
                    [u'是否激活', u'禁用', u'激活']

        else:
            alert_info = [field_name, unicode(value[0]), unicode(value[1])]

        if 'alert_info' in dir():
            alert_list.append(alert_info)

    if alert_list:
        AssetRecord.objects.create(asset=asset, username=username, content=alert_list)


def ansible_record(asset, ansible_dic, username):
    alert_dic = {}
    asset_dic = asset.__dict__
    eth_info = ansible_dic.pop('eth_info')
    for field, value in ansible_dic.items():
        old = asset_dic.get(field)
        new = ansible_dic.get(field)
        if unicode(old) != unicode(new):
            setattr(asset, field, value)
            asset.save()
            alert_dic[field] = [old, new]

    # 更新网卡信息
    asset_net = asset.networking.all()[0]
    if asset_net.net_name in eth_info.keys():
        asset_net.active = eth_info[asset_net.net_name]['active']
        asset_net.device = eth_info[asset_net.net_name]['device']
        asset_net.macaddress = eth_info[asset_net.net_name]['macaddress']
        asset_net.mtu = eth_info[asset_net.net_name]['mtu']
        asset_net.module = eth_info[asset_net.net_name]['module']
        asset_net.pciid = eth_info[asset_net.net_name]['pciid']
        asset_net.promisc = eth_info[asset_net.net_name]['promisc']
        asset_net.type = eth_info[asset_net.net_name]['type']
        asset_net.save()
    elif asset_net.net_name not in eth_info.keys() and len(eth_info.keys()) == 1:
        new_eth_info = eth_info.values()[0]
        asset_net.net_name = new_eth_info['device']
        asset_net.active = new_eth_info['active']
        asset_net.device = new_eth_info['device']
        asset_net.macaddress = new_eth_info['macaddress']
        asset_net.module = new_eth_info['module']
        asset_net.mtu = new_eth_info['mtu']
        asset_net.pciid = new_eth_info['pciid']
        asset_net.promisc = new_eth_info['promisc']
        asset_net.type = new_eth_info['type']
        asset_net.save()
    db_asset_alert(asset, username, alert_dic)


def excel_to_db(excel_file):
    """
    Asset add batch function
    """
    asset_name_list = []
    try:
        data = xlrd.open_workbook(filename=None, file_contents=excel_file.read())
    except Exception, e:
        return False
    else:
        table = data.sheets()[0]
        rows = table.nrows
        for row_num in range(1, rows):
            row = table.row_values(row_num)
            if row:
                group_instance = []
                ip, port, hostname, use_default_auth, username, password, group = row
                if get_object(Asset, hostname=hostname):
                    continue
                if isinstance(password, int) or isinstance(password, float):
                    password = unicode(int(password))
                use_default_auth = 1 if use_default_auth == u'默认' else 0
                password_encode = CRYPTOR.encrypt(password) if password else ''
                if hostname:
                    asset = Asset(ip=ip,
                                  port=port,
                                  hostname=hostname,
                                  use_default_auth=use_default_auth,
                                  username=username,
                                  password=password_encode
                                  )
                    asset.save()
                    group_list = group.split('/')
                    for group_name in group_list:
                        group = get_object(AssetGroup, name=group_name)
                        if group:
                            group_instance.append(group)
                    if group_instance:
                        asset.group = group_instance
                    asset.save()
                    asset_name_list.append(hostname)
        return True,asset_name_list


def get_ansible_asset_info(asset_ip, setup_info):
    disk_need = {}
    disk_all = setup_info.get("ansible_devices")
    if disk_all:
        for disk_name, disk_info in disk_all.iteritems():
            if disk_name.startswith('sd') or disk_name.startswith('hd') or disk_name.startswith('vd') or disk_name.startswith('xvd'):
                disk_size = disk_info.get("size", '')
                if 'M' in disk_size:
                    disk_format = round(float(disk_size[:-2]) / 1000, 0)
                elif 'T' in disk_size:
                    disk_format = round(float(disk_size[:-2]) * 1000, 0)
                else:
                    disk_format = float(disk_size[:-2])
                disk_need[disk_name] = disk_format
    all_ip = setup_info.get("ansible_all_ipv4_addresses")
    other_ip_list = all_ip.remove(asset_ip) if asset_ip in all_ip else []
    other_ip = ','.join(other_ip_list) if other_ip_list else ''
    product_name = setup_info.get("ansible_product_name")
    product_uuid = setup_info.get("ansible_product_uuid")
    product_version = setup_info.get("ansible_product_version")
    system_vendor = setup_info.get("ansible_system_vendor")
    devices = setup_info.get("ansible_devices")
    try:
        cpu_type = setup_info.get("ansible_processor")[1]
    except IndexError:
        cpu_type = ' '.join(setup_info.get("ansible_processor")[0].split(' ')[:6])

    memory = setup_info.get("ansible_memtotal_mb")
    try:
        memory_format = int(round((int(memory) / 1000), 0))
    except Exception:
        memory_format = memory
    disk = disk_need
    system_type = setup_info.get("ansible_distribution")
    if system_type.lower() == "freebsd":
        system_version = setup_info.get("ansible_distribution_release")
        cpu_cores = setup_info.get("ansible_processor_count")
    else:
        system_version = setup_info.get("ansible_distribution_version")
        cpu_cores = setup_info.get("ansible_processor_vcpus")
    cpu = cpu_type + ' * ' + unicode(cpu_cores)
    system_arch = setup_info.get("ansible_architecture")
    product_serial = setup_info.get("ansible_product_serial")
    bios_date = setup_info.get("ansible_bios_date")
    bios_version = setup_info.get("ansible_bios_version")
    interfaces = setup_info.get("ansible_interfaces")
    eth_info = {}
    for item in interfaces:
        if item.startswith('eth'):
                eth_info[item] = setup_info.get("ansible_%s"%item)
    asset_info = [other_ip, cpu, memory_format, disk, product_serial, system_type, devices,
                  system_version, product_name, system_arch, bios_date, bios_version,
                  product_uuid, product_version, system_vendor, eth_info]
    return asset_info


def asset_ansible_update(obj_list, ansible_asset_info, name):
    for asset in obj_list:
        try:
            ip = asset.networking.all()[0].ip_address
            setup_info = ansible_asset_info['messege']['success'][ip]['ansible_facts']
        except KeyError, e:
            logger.error("获取setup_info失败: %s" % e)
            continue
        else:
            try:
                asset_info = get_ansible_asset_info(asset.ip, setup_info)
                other_ip, cpu, memory, disk, product_serial, system_type, devices,\
                system_version, product_name, system_arch, bios_date, bios_version,\
                product_uuid, product_version, system_vendor, eth_info = asset_info
                asset_dic = {"other_ip": other_ip,
                             "cpu": cpu,
                             "memory": memory,
                             "disk": disk,
                             "product_serial": product_serial,
                             "product_name": product_name,
                             "product_uuid": product_uuid,
                             "product_version": product_version,
                             "system_type": system_type,
                             "devices": devices,
                             "system_version": system_version,
                             "system_arch": system_arch,
                             "bios_date": bios_date,
                             "bios_version": bios_version,
                             "system_vendor": system_vendor,
                             "eth_info": eth_info
                             }
                ansible_record(asset, asset_dic, name)
            except Exception as e:
                logger.error("save setup info failed! %s" % e)
                traceback.print_exc()


def asset_ansible_update_all():
    name = u'定时更新'
    asset_all = Asset.objects.all()
    asset_ansible_update(asset_all, name)


def gen_proxy_profiles(proxys):
    """
    获取proxy对应的profiles
    """
    proxy_profiles = {}
    if isinstance(proxys, (list, QuerySet)):
        for item in proxys:
            profiles = []
            try:
                api = APIRequest('{0}/v1.0/profile'.format(item.url), item.username, CRYPTOR.decrypt(item.password))
                msg, codes = api.req_get()
                if msg:
                    profiles = msg['profiles']
            except Exception as e:
                logger.error(e)
            proxy_profiles[item.proxy_name] = profiles
    logger.info("获取proxy对应的profiles:%s"%proxy_profiles)
    return proxy_profiles


def gen_asset_proxy(asset_list):
    """
    {'proxy_1':[asset1, asset2], 'proxy_2':[asset3,asset4]}
    """
    asset_proxys = {}
    proxy_set = set([asset.proxy.proxy_name for asset in asset_list])
    for item in proxy_set:
        asset_proxys[item] = []
        for asset in asset_list:
            if asset.proxy.proxy_name == item:
                asset_proxys[item].append(asset)
    logger.info('获取不同proxy所拥有的主机asset_proxys: %s'% asset_proxys)
    return asset_proxys


def get_group_names(group_list):
    """
    获取用户组的名字 'group1 group2 ...'
    """
    if len(group_list) < 3:
        return ' '.join([group.name for group in group_list])
    else:
        return '%s ...' % ' '.join([group.name for group in group_list[0:2]])


def get_disk_info(disk_info):
    """
    获取硬盘信息
    """
    try:
        disk_size = 0
        if disk_info:
            disk_dic = ast.literal_eval(disk_info)
            for disk, size in disk_dic.items():
                disk_size += size
            disk_size = int(disk_size)
        else:
            disk_size = ''
    except Exception:
        disk_size = disk_info
    return disk_size
