from python.shared.shared import *


def send_txt_msg(text_string, wx_id):
    """
    发送文本消息
    :param text_string: 文本内容
    :param wx_id: 微信ID
    :return:
    """
    qs = {
        "id": get_id(),
        "type": TXT_MSG,
        "wxid": wx_id,
        "roomid": "",
        "content": text_string,  # 文本消息内容
        "nickname": "",
        "ext": ""
    }
    s = json.dumps(qs)
    return s


def send_at_meg(wx_id, room_id, content, nickname):
    """
    发送at消息
    :param wx_id:
    :param room_id:
    :param content:
    :param nickname:
    :return:
    """
    qs = {
        "id": get_id(),
        "type": AT_MSG,
        "wxid": wx_id,
        "roomid": room_id,
        "content": content,
        "nickname": nickname,
        "ext": "null"
    }
    s = json.dumps(qs)
    return s


def send_pic_msg(wx_id, content):
    """
    发送图片消息
    :param wx_id:
    :param content:
    :return:
    """
    qs = {
        "id": get_id(),
        "type": PIC_MSG,
        "wxid": wx_id,
        "roomid": "",
        "content": content,
        "nickname": "",
        "ext": ""
    }
    s = json.dumps(qs)
    return s


def send_wxuser_list():
    """
    发送用户列表
    :return:
    """
    qs = {
        "id": get_id(),
        "type": USER_LIST,
        "wxid": "",
        "roomid": "",
        "content": "",
        "nickname": "",
        "ext": ""
    }
    s = json.dumps(qs)
    return s
