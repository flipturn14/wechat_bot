import os.path
import re

import websocket
import xmltodict

from python.basic.get import *
from python.basic.send import send_txt_msg
from python.basic.task import global_wx_dict, ImgTask, ChatTask
from python.basic.tools import get_now
from python.multithread.threads import img_que, chat_que, Processor

from python.revChat.poe.poe import Poe
from python.revChat.xeasy import Xeasy
from python.revChat.yqcloud import YQcloud
from python.shared.shared import *

# 公共线程
global_thread = []
# 屏蔽id集合，重启失效
user_configs = {}

welcome_group = "调用GPT对话请在文字前增加召唤字母\n" \
                "可用功能为g/c，例如：\ng你是谁？\n" \
                "有时候因为连接国外网络出问题不回答时请使用c为首字母进行提问"

welcome_private = "当前是关闭自动回复状态，开启后直接对话即可，无需增加首字母\n" \
                  "如需启用自动回复请输入：开启\n" \
                  "如需关闭自动回复请输入：关闭\n" \
                  "有时候因为连接国外网络出问题不回答时请使用c为首字母进行提问"


def debug_switch():
    print("debug_switch")
    qs = {
        "id": get_id(),
        "type": DEBUG_SWITCH,
        "content": "off",
        "wxid": "",
    }
    s = json.dumps(qs)
    return s


def handle_nick(j):
    print("handle_nick", j)
    data = json.loads(j["content"])
    wxid = str(data['wxid'])
    # print("群成员昵称：" + data["nick"] + " wxid = " + wxid)
    # 昵称对应关系记录到集合中，不同群有相同id的，不会覆盖
    global_wx_dict[wxid] = data["nick"]


def handle_at_msg(j):
    print("handle_at_msg", j)
    data = json.loads(j["content"])
    wxid = str(data['wxid'])
    # print("群成员昵称：" + data["nick"] + " wxid = " + wxid)
    # 昵称对应关系记录到集合中，不同群有相同id的，不会覆盖
    global_wx_dict[wxid] = data["nick"]


def handle_member_list(j):
    print("handle_member_list", j)
    data = j["content"]
    print(data)


def destroy_all():
    print("destroy_all")
    qs = {
        "id": get_id(),
        "type": DESTROY_ALL,
        "content": "none",
        "wxid": "node",
    }
    s = json.dumps(qs)
    return s


def handle_wxuser_list(j):
    print("handle_wxuser_list")
    content = j["content"]
    i = 0
    # 微信群
    for item in content:
        i += 1
        id = item["wxid"]
        m = id.find("@")
        if m != -1:
            print(i, "群聊", id, item["name"])
            global_wx_dict[id] = item["name"]

    # 微信其他好友，公众号等
    for item in content:
        i += 1
        id = item["wxid"]
        m = id.find("@")
        if m == -1:
            print(i, "个体", id, item["name"], item["wxcode"])
            global_wx_dict[id] = item["name"]


poe_objs = {}


def handle_recv_txt_msg(j):
    # ----------基础信息begin----------
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
    # 没有昵称的把wx_id作为昵称
    nick = (global_wx_dict.get(wx_id) if global_wx_dict.get(wx_id) else wx_id) + "[" + wx_id + "]"
    if is_room:
        room_name = (global_wx_dict.get(room_id) if global_wx_dict.get(room_id) else room_id)
        nick += "[" + room_name + "]" + "[" + room_id + "]"
    # ----------基础信息end----------
    # 输出所有消息
    print(get_now() + nick + "：" + content)
    # 判断对话内容是否为添加VIP
    if add_vip(wx_id, content):
        return
    # 判断当前状态是否为禁止对话
    if change_status(wx_id, nick, content, is_room, room_id):
        return
    # 已关闭群聊的room_id或关闭自动回复的wxid，直接返回
    if (is_room and user_configs[room_id]["disable"]) or \
            (is_room is False and user_configs.get(wx_id) is None) or \
            (is_room is False and user_configs[wx_id]["disable"]):
        return

    # 启用了生成图片并且起始关键字一致
    if stableDiffRly and (
            (content.startswith(privateImgKey) and not is_room) or (content.startswith(groupImgKey) and is_room)):
        content = re.sub("^" + (groupImgKey if is_room else privateImgKey), "", content, 1)
        if check_interval(wx_id, content, is_room, room_id):
            return
        user_configs[wx_id]["last_time"] = time.time()
        ig = ImgTask(ws, content, wx_id, room_id, is_room)
        img_que.put(ig)
    elif (content.startswith(privateChatKey) and not is_room) or (
            content.startswith(groupChatKey) and is_room) or (
            content.startswith(groupChatKey3) and is_room) or (
            content.startswith(groupChatKey4) and is_room):
        if check_interval(wx_id, content, is_room, room_id):
            return
        user_configs[wx_id]["last_time"] = time.time()
        if is_room:
            if content.startswith(groupChatKey):
                replace = re.sub("^" + groupChatKey, "", content, 1)
                print(get_now() + "[" + room_id + "]群聊，Poe")
                if poe_objs.get(room_id) is None:
                    chatbot = Poe(room_id)
                    poe_objs[room_id] = chatbot
                else:
                    chatbot = poe_objs[room_id]
            elif content.startswith(groupChatKey3):
                replace = re.sub("^" + groupChatKey3, "", content, 1)
                print(get_now() + "[" + room_id + "]群聊，XEasy")
                chatbot = Xeasy(room_id)
            else:
                replace = re.sub("^" + groupChatKey4, "", content, 1)
                print(get_now() + "[" + room_id + "]群聊，YQcloud")
                chatbot = YQcloud(room_id)
        else:
            replace = re.sub("^" + privateChatKey, "", content, 1)
            if content.startswith(groupChatKey3):
                print(get_now() + "[" + wx_id + "]私聊，XEasy")
                chatbot = Xeasy(wx_id)
            elif content.startswith(groupChatKey4):
                print(get_now() + "[" + wx_id + "]私聊，YQcloud")
                chatbot = YQcloud(wx_id)
            else:
                replace = re.sub("^" + groupChatKey, "", content, 1)
                print(get_now() + "[" + wx_id + "]私聊，Poe")
                if poe_objs.get(wx_id) is None:
                    chatbot = Poe(wx_id)
                    poe_objs[wx_id] = chatbot
                else:
                    chatbot = poe_objs[wx_id]
        # 创建聊天任务并放入消息队列
        ct = ChatTask(ws, replace, chatbot, wx_id, room_id, is_room, is_citation)
        chat_que.put(ct)
    # 获取微信昵称
    find_nick(wx_id, room_id)


def change_status(wx_id, nick, content, is_room, room_id):
    if is_room:  # 群内消息
        if user_configs.get(room_id) is None:
            print(get_now() + nick + "配置文件没有存储该群聊信息，默认关闭。保存至文件")
            init_user(room_id)
            if poe_objs.get(room_id) is None:
                chatbot = Poe(room_id)
                poe_objs[room_id] = chatbot
        if wx_id in group_admin:
            if content.startswith(groupChatKey + "关闭"):
                user_configs[room_id]["disable"] = True
                ws.send(send_txt_msg(text_string="已经关闭该群的回复，大家再见！", wx_id=room_id))
                save_config()
                return True
            elif content.startswith(groupChatKey + "开启"):
                user_configs[room_id]["disable"] = False
                ws.send(send_txt_msg(text_string="大家好，" + welcome_group, wx_id=room_id))
                save_config()
                return True
    else:  # 个人消息
        if user_configs.get(wx_id) is None:
            print(get_now() + nick + "配置文件没有存储该用户信息，默认关闭。保存至文件")
            init_user(wx_id)
            if poe_objs.get(wx_id) is None:
                chatbot = Poe(wx_id)
                poe_objs[wx_id] = chatbot
            ws.send(send_txt_msg(text_string=welcome_private, wx_id=wx_id))
        if content == "关闭":
            user_configs[wx_id]["disable"] = True
            ws.send(send_txt_msg(text_string="已经关闭自动回复，如需恢复请输入：开启", wx_id=wx_id))
            save_config()
            return True
        elif content == "开启":
            user_configs[wx_id]["disable"] = False
            ws.send(send_txt_msg(text_string="已经开启自动回复，如需停用请输入：关闭", wx_id=wx_id))
            save_config()
            return True
        elif content == "你好" or content.startswith("在吗") or content.startswith("在么"):
            ws.send(send_txt_msg(text_string=welcome_private, wx_id=wx_id))
            return True
        elif user_configs[wx_id]["disable"]:
            ws.send(send_txt_msg(text_string=welcome_private, wx_id=wx_id))
    return False


def add_vip(wx_id, content):
    # 添加VIP用户
    if wx_id in group_admin:
        if content.startswith(groupChatKey + "添加"):
            nick = re.sub("^" + groupChatKey + "添加", "", content, 1)
            wx_id = get_wx_id(nick)
            if user_configs.get(wx_id) is not None:
                user_configs[wx_id]['vip'] = True
                save_config()
                ws.send(send_txt_msg(text_string="添加成功，该用户无限制", wx_id=wx_id))
            elif user_configs.get(nick) is not None:
                user_configs[wx_id]['vip'] = True
                save_config()
                ws.send(send_txt_msg(text_string="添加成功，该用户无限制", wx_id=nick))
            else:
                ws.send(send_txt_msg(text_string="此用户不存在", wx_id=wx_id))
            return True
        elif content.startswith(groupChatKey + "删除"):
            nick = re.sub("^" + groupChatKey + "删除", "", content, 1)
            wx_id = get_wx_id(nick)
            if user_configs.get(wx_id) is not None:
                user_configs[wx_id]['vip'] = False
                ws.send(send_txt_msg(text_string="删除成功，该用户受限制", wx_id=wx_id))
                save_config()
            else:
                ws.send(send_txt_msg(text_string="此用户不存在", wx_id=wx_id))
            return True
        elif content.startswith(groupChatKey + "通过"):
            nick = re.sub("^" + groupChatKey + "通过", "", content, 1)
            wx_id = get_wx_id(nick)
            if user_configs.get(wx_id) is not None:
                ws.send(send_txt_msg(text_string="此用户不存在", wx_id=wx_id))
                save_config()
            else:
                ws.send(send_txt_msg(text_string="此用户不存在", wx_id=wx_id))
            return True
    return False


def init_user(wx_id):
    user_configs[wx_id] = {
        "disable": True,
        "last_time": time.time() - chat_interval - 1,
        "vip": False
    }
    save_config()


def check_interval(wx_id, content, is_room, room_id):
    # 计算聊天间隔，不判断VIP用户以及管理员
    if user_configs.get(wx_id) is None:
        init_user(wx_id)
    last_time = user_configs[wx_id]["last_time"]
    interval = int(time.time() - last_time)
    if interval < chat_interval and (wx_id not in group_admin and user_configs[wx_id]["vip"] is not True):
        tip_content = ("小于设定提问间隔时间%d秒，还需等待%d秒" % (chat_interval, (chat_interval - interval)))
        # if interval < chat_interval:
        #     print(("小于设定提问间隔时间%d秒，还需等待%d秒" % (chat_interval, (chat_interval - interval))))
        # if wx_id not in group_admin:
        #     print("不是管理员")
        # if user_configs[wx_id]["vip"] is not True:
        #     print("不是VIP")
        if is_room:
            nick = find_nick(wx_id, room_id)
            tip_content = nick + "：" + content + "\n--------------------\n" + tip_content
            ws.send(send_txt_msg(text_string=tip_content, wx_id=room_id))
        else:
            ws.send(send_txt_msg(text_string=tip_content, wx_id=wx_id))
        return True
    return False


def get_wx_id(nick):
    for wx_id, value in global_wx_dict.items():
        if value == nick:
            return wx_id
    return nick


def find_nick(wx_id, room_id):
    if wx_id is not None:
        nick = global_wx_dict.get(wx_id)
        if nick is None:
            ws.send(get_chat_nick_p(wx_id, room_id))
            return wx_id
        else:
            return nick


def handle_recv_pic_msg(j):
    print("handle_recv_pic_msg", j)


def handle_recv_txt_cite(j):
    print("handle_recv_txt_cite", j)


def handle_new_friend_request(j):
    print("handle_new_friend_request")
    xml = j["content"]
    data_dict = xmltodict.parse(xml)
    print("fromusername = " + data_dict['msg']["@fromusername"])
    print("content = " + data_dict['msg']["@content"])
    print("fromusername = " + data_dict['msg']["@fromusername"])
    wxid = data_dict['msg']["fromnickname"]
    nick = data_dict['msg']['fullpy']
    content = data_dict['msg']["content"]
    print(f"添加好友请求wx_id[{wxid}]nick[{nick}]content[{content}]")
    global_wx_dict[wxid] = nick


def handle_agree_to_friend_request(j):
    print("handle_agree_to_friend_request", j)


def handle_other_msg(j):
    print(j)
    data = j["content"]
    room_id = data["id1"]
    content: str = data["content"].strip()
    if content.endswith("加入了群聊"):
        nick = content.split('"邀请"')[1].split('"')[0]
        ws.send(send_txt_msg(text_string="欢迎" + nick + "入群，" + welcome_group, wx_id=room_id))
    elif content.endswith("分享的二维码加入群聊"):
        nick = content.split('"')[1]
        ws.send(send_txt_msg(text_string="欢迎" + nick + "入群，" + welcome_group, wx_id=room_id))
    elif content.endswith("现在可以开始聊天了。"):
        ws.send(send_txt_msg(text_string=welcome_private, wx_id=room_id))


def handle_heartbeat(j):
    pass


def on_open(ws):
    ws.send(get_personal_info())
    ws.send(get_contact_list())
    # 创建聊天处理线程
    chat_processor = Processor(chat_que)
    global_thread.append(chat_processor)
    # 创建图片处理线程
    for i in range(0, 4):
        image_processor = Processor(img_que)
        global_thread.append(image_processor)
    load_config()
    print(get_now() + "启动成功")


def on_message(ws, message):
    if "execption" == message:
        return
    j = json.loads(message)
    resp_type = j["type"]

    action = {
        HEART_BEAT: handle_heartbeat,
        RECV_TXT_MSG: handle_recv_txt_msg,
        RECV_PIC_MSG: handle_recv_pic_msg,
        NEW_FRIEND_REQUEST: handle_new_friend_request,
        AGREE_TO_FRIEND_REQUEST: handle_agree_to_friend_request,
        RECV_TXT_CITE_MSG: handle_recv_txt_cite,

        TXT_MSG: print,
        PIC_MSG: print,
        AT_MSG: handle_at_msg,

        USER_LIST: handle_wxuser_list,
        GET_USER_LIST_SUCCESS: handle_wxuser_list,
        GET_USER_LIST_FAIL: handle_wxuser_list,
        ATTACH_FILE: print,

        CHATROOM_MEMBER: handle_member_list,
        CHATROOM_MEMBER_NICK: handle_nick,
        DEBUG_SWITCH: print,
        PERSONAL_INFO: print,
        PERSONAL_DETAIL: print,
        OTHER_REQUEST: handle_other_msg
    }

    action.get(resp_type, print)(j)


def on_error(ws, error):
    print(ws)
    print(error)


def on_close(ws):
    print(ws)
    print("closed")


def save_config():
    # print("保存已关闭聊天id配置到文件")
    data = json.dumps(user_configs)
    with open("./data.json", "wb") as file_object:
        file_object.write(data.encode('utf-8'))
    file_object.close()
    print("保存用户配置到文件完成")


def load_config():
    global user_configs
    print("读取用户配置到文件")
    if os.path.exists("./data.json"):
        with open("./data.json", encoding="utf-8") as file_object:
            user_configs = json.load(file_object)
        file_object.close()
        print("读取用户配置到文件完成")
    else:
        print("未找用户消息配置文件")


server = "ws://" + server_host
# 是否调试模式
# websocket.enableTrace(False)
websocket.enableTrace(True)

ws = websocket.WebSocketApp(server, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
