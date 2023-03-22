import re

import websocket

from python.basic.get import get_chat_nick_p, get_personal_info
from python.basic.send import send_txt_msg
from python.basic.task import global_wx_dict, ImgTask, ChatTask
from python.basic.tools import get_now
from python.multithread.threads import img_que, chat_que, Processor
from python.revChat.gpt4 import Gpt4
from python.revChat.poe import Poe
from python.shared.shared import *

# 公共线程
global_thread = []
# 屏蔽群聊集合，重启失效
disable_group = {}
# 收到信息立即回复群聊集合
auto_group = {}
# 群内默认管理员ID
group_admin = {'admin'}


def debug_switch():
    qs = {
        "id": get_id(),
        "type": DEBUG_SWITCH,
        "content": "off",
        "wxid": "",
    }
    s = json.dumps(qs)
    return s


def handle_nick(j):
    data = json.loads(j["content"])
    wxid = str(data['wxid'])
    # print("群成员昵称：" + data["nick"] + " wxid = " + wxid)
    # 昵称对应关系记录到集合中，不同群有相同id的，不会覆盖
    global_wx_dict[wxid] = data["nick"]


def handle_member_list(j):
    data = j["content"]
    print(data)


def destroy_all():
    qs = {
        "id": get_id(),
        "type": DESTROY_ALL,
        "content": "none",
        "wxid": "node",
    }
    s = json.dumps(qs)
    return s


def handle_wxuser_list(j):
    content = j["content"]
    i = 0
    # 微信群
    for item in content:
        i += 1
        id = item["wxid"]
        m = id.find("@")
        if m != -1:
            print(i, "群聊", id, item["name"])

    # 微信其他好友，公众号等
    for item in content:
        i += 1
        id = item["wxid"]
        m = id.find("@")
        if m == -1:
            print(i, "个体", id, item["name"], item["wxcode"])


def handle_recv_txt_msg(j):
    wx_id = j["wxid"]
    room_id = ""
    content: str = j["content"].strip()

    is_room: bool

    if len(wx_id) < 9 or wx_id[-9] != "@":
        is_room = False
        wx_id: str = j["wxid"]
    else:
        is_room = True
        wx_id = j["id1"]
        room_id = j["wxid"]
    is_citation = (grpCitationMode and is_room) or (prvCitationMode and not is_room)
    # 默认群内自动回复关闭
    if is_room and auto_group.get(room_id) is None:
        auto_group[room_id] = "关闭"
    if is_room and wx_id in group_admin:
        if content.startswith("g关闭"):
            disable_group[room_id] = "关闭"
            print(get_now() + "当前状态" + str(disable_group.get(room_id)))
            ws.send(send_txt_msg(text_string="已经关闭该群的回复，大家再见！", wx_id=room_id))
            return
        elif content.startswith("g启用"):
            if disable_group.get(room_id) is not None:
                del disable_group[room_id]
            ws.send(send_txt_msg(
                text_string="大家好，请在文字前增加召唤字母\n"
                            "可用功能为c/g/t\n"
                            "c=ChatGPT-4 没有上下文关联\n"
                            "g=ChatGPT-3 支持上下文关联\n"
                            "t=生成图片",
                wx_id=room_id))
            return
        elif content.startswith("燃烧吧小宇宙"):  # 谨慎开启，群内消息过接口会承载不了
            auto_group[room_id] = "开启"
            ws.send(send_txt_msg(text_string="已经开始燃烧", wx_id=room_id))
            return
        elif content.startswith("阿门"):
            auto_group[room_id] = "关闭"
            ws.send(send_txt_msg(text_string="火焰已经熄灭", wx_id=room_id))
            return
    # 该群已关闭群聊，直接返回
    if disable_group.get(room_id) is not None:
        # print(get_now() + "该群已关闭群聊")
        return
    replace = content
    # 启用了生成图片并且起始关键字一致
    if stableDiffRly and (
            (content.startswith(privateImgKey) and not is_room) or (content.startswith(groupImgKey) and is_room)):
        content = re.sub("^" + (groupImgKey if is_room else privateImgKey), "", content, 1)
        ig = ImgTask(ws, content, wx_id, room_id, is_room)
        img_que.put(ig)
    elif (content.startswith(privateChatKey) and not is_room) or (
            content.startswith(groupChatKey) and is_room) or (
            content.startswith(groupChatKey4) and is_room) or (
            auto_group.get(room_id) is not None and auto_group[room_id] == "开启"):
        if is_room:
            if content.startswith(groupChatKey):
                replace = re.sub("^" + groupChatKey, "", content, 1)
            else:
                replace = re.sub("^" + groupChatKey4, "", content, 1)
        else:
            replace = re.sub("^" + privateChatKey, "", content, 1)
        if is_room:  # 如果是群聊，通过房间号创建机器人
            if content.startswith(groupChatKey):
                print(get_now() + "[" + room_id + "]群聊，Poe")
                chatbot = Poe(room_id)
            else:
                print(get_now() + "[" + room_id + "]群聊，GPT4")
                chatbot = Gpt4(room_id)
        else:  # 不是群聊，通过微信ID创建机器人
            print(get_now() + "[" + wx_id + "]新创建微信信息，私聊")
            if content.startswith(groupChatKey):
                chatbot = Poe(wx_id)
            else:
                chatbot = Gpt4(wx_id)
        # 创建聊天任务并放入消息队列
        ct = ChatTask(ws, replace, chatbot, wx_id, room_id, is_room, is_citation)
        chat_que.put(ct)
    # 打印所有未屏蔽的消息
    print(
        get_now() + (global_wx_dict.get(wx_id) if global_wx_dict.get(wx_id) else wx_id) + "[" + wx_id + "]：" + replace)
    # 获取微信昵称
    if wx_id is not None:
        nick = global_wx_dict.get(wx_id)
        if nick is None:
            ws.send(get_chat_nick_p(wx_id, room_id))


def handle_recv_pic_msg(j):
    pass


def handle_recv_txt_cite(j):
    pass


def handle_heartbeat(j):
    pass


def on_open(ws):
    ws.send(get_personal_info())
    # 创建聊天处理线程
    chat_processor = Processor(chat_que)
    global_thread.append(chat_processor)
    # 创建图片处理线程
    for i in range(0, 4):
        image_processor = Processor(img_que)
        global_thread.append(image_processor)
    print(get_now() + "启动成功")
    # 通知微信号已进行重启
    # ws.send(send_txt_msg(text_string="启动完毕，已就绪", wx_id=""))


def on_message(ws, message):
    if "execption" == message:
        return
    j = json.loads(message)
    resp_type = j["type"]
    action = {
        HEART_BEAT: handle_heartbeat,
        RECV_TXT_MSG: handle_recv_txt_msg,
        RECV_PIC_MSG: handle_recv_pic_msg,
        NEW_FRIEND_REQUEST: print,
        RECV_TXT_CITE_MSG: handle_recv_txt_cite,

        TXT_MSG: print,
        PIC_MSG: print,
        AT_MSG: print,

        USER_LIST: handle_wxuser_list,
        GET_USER_LIST_SUCCESS: handle_wxuser_list,
        GET_USER_LIST_FAIL: handle_wxuser_list,
        ATTACH_FILE: print,

        CHATROOM_MEMBER: handle_member_list,
        CHATROOM_MEMBER_NICK: handle_nick,
        DEBUG_SWITCH: print,
        PERSONAL_INFO: print,
        PERSONAL_DETAIL: print,
    }

    action.get(resp_type, print)(j)


def on_error(ws, error):
    print(ws)
    print(error)


def on_close(ws):
    print(ws)
    print("closed")


server = "ws://" + server_host
# 是否调试模式
websocket.enableTrace(False)

ws = websocket.WebSocketApp(server, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
