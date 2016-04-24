# coding:utf-8
from django import forms

from assetManage.models import IDC, Asset, AssetGroup,NetWorkingGlobal,NetWorking,PowerManage


class AssetForm(forms.ModelForm):

    class Meta:
        model = Asset

        fields = [
            "ip", "other_ip", 'name', 'owerns', 'profice', 'status','kickstart', 'netboot_enabled', "port", "group", "proxy",'username','password', 'networking_g', 'networking', 'power_manage',
            "idc", "brand", "cpu", "memory", "disk", "system_type", "system_version", "cabinet", "position", "number", "machine_status", "asset_type", "env", "sn", "is_active", "comment",
            "system_arch"
        ]


class NetWorkingGlobalForm(forms.ModelForm):
    class Meta:
        model = NetWorkingGlobal

        fields = ['hostname', 'gateway', 'name_servers']


class NetWorkingForm(forms.ModelForm):
    class Meta:
        model = NetWorking

        exclude = []


class PowerManageForm(forms.ModelForm):
    class Meta:
        model = PowerManage

        exclude = []


class AssetGroupForm(forms.ModelForm):
    class Meta:
        model = AssetGroup
        fields = [
            "name", "comment"
        ]


class IdcForm(forms.ModelForm):
    class Meta:
        model = IDC
        fields = ['name', "bandwidth", "operator", 'linkman', 'phone', 'address', 'network', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Name'}),
            'network': forms.Textarea(
                attrs={'placeholder': '192.168.1.0/24\n192.168.2.0/24'})
        }


