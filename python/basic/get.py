# -*- coding: utf-8 -*-

from python.shared.shared import *


def get_chatroom_memberlist(wx_id, room_id):
    """
    获取群成员列表
    :return:
    """
    qs = {
        "id": get_id(),
        "type": CHATROOM_MEMBER,
        "wxid": wx_id,
        "roomid": room_id,
        "content": "",
        "nickname": "",
        "ext": ""
    }
    s = json.dumps(qs)
    return s


def get_chat_nick_p(wx_id, room_id):
    """
    获取群成员昵称
    :param wx_id: 微信ID
    :param room_id: 房间ID
    :return:
    """
    qs = {
        "id": get_id(),
        "type": CHATROOM_MEMBER_NICK,
        "wxid": wx_id,
        "roomid": room_id,
        "content": "",
        "nickname": "",
        "ext": ""
    }
    s = json.dumps(qs)
    return s


def get_personal_info():
    """
    获取本号码信息
    :return:
    """
    qs = {
        "id": get_id(),
        "type": PERSONAL_INFO,
        "wxid": "ROOT",
        "roomid": "",
        "content": "",
        "nickname": "",
        "ext": ""
    }
    s = json.dumps(qs)
    return s


def get_personal_detail(wx_id):
    """
    获取本号码详情
    :param wx_id:
    :return:
    """
    qs = {
        "id": get_id(),
        "type": PERSONAL_DETAIL,
        "wxid": wx_id,
        "roomid": "",
        "content": "",
        "nickname": "",
        "ext": ""
    }
    s = json.dumps(qs)
    return s


def get_contact_list():
    j = {
        "id": get_id(),
        "type": USER_LIST,
        "roomid": 'null',
        "wxid": 'null',  # not null
        "content": 'null',  # not null
        "nickname": 'null',
        "ext": 'null'
    }
    return json.dumps(j)
