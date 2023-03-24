import os.path
import re
import time

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
# 屏蔽id集合，重启失效
user_configs = {}

welcome_group = "调用GPT对话请在文字前增加召唤字母\n" \
                "可用功能为c/g/t\n" \
                "c=ChatGPT-4 没有上下文关联\n" \
                "g=ChatGPT-3 支持上下文关联\n" \
                "t=生成图片\n" \
                "您也可以尝试自己搭建，地址https://github.com/flipturn14/wechat_bot\n" \
                "如果感觉好用，请在github上点击一个star"

welcome_private = "当前是关闭自动回复状态\n" \
                  "如需启用自动回复请输入：开启\n" \
                  "如需关闭自动回复请输入：关闭\n" \
                  "您可以直接发送文字给我，默认使用ChatGPT-4 没有上下文关联；\n" \
                  "如需要上下文，请在说话前增加g，增加t为生成图片\n" \
                  "连续问的问题太多，会因为微信本身策略限制并提示我：[发送消息过于频繁，可稍后再试]\n" \
                  "这样会造成我无法回复消息给您，甚至封号，所以请您不要连续提问太多问题，可以隔一段时间再试，谢谢。\n" \
                  "您也可以尝试自己搭建，地址https://github.com/flipturn14/wechat_bot\n" \
                  "如果感觉好用，请在github上点击一个star"


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
        nick += "[" + room_id + "]"
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
        # if is_room and user_configs[room_id]["disable"]:
        #     print("已关闭群聊")
        # elif is_room is False and user_configs.get(wx_id) is None:
        #     print("没有找到用户信息")
        # elif is_room is False and user_configs[wx_id]["disable"]:
        #     print("已关闭自动回复")
        # else:
        #     print("未捕获")
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
            content.startswith(groupChatKey4) and is_room):
        if check_interval(wx_id, content, is_room, room_id):
            return
        user_configs[wx_id]["last_time"] = time.time()
        if is_room:
            if content.startswith(groupChatKey):
                replace = re.sub("^" + groupChatKey, "", content, 1)
            else:
                replace = re.sub("^" + groupChatKey4, "", content, 1)
            if content.startswith(groupChatKey):
                print(get_now() + "[" + room_id + "]群聊，Poe")
                chatbot = Poe(room_id)
            else:
                print(get_now() + "[" + room_id + "]群聊，GPT4")
                chatbot = Gpt4(room_id)
        else:
            replace = re.sub("^" + privateChatKey, "", content, 1)
            print(get_now() + "[" + wx_id + "]新创建微信信息，私聊")
            if content.startswith(groupChatKey):
                chatbot = Poe(wx_id)
            else:
                chatbot = Gpt4(wx_id)
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
            ws.send(send_txt_msg(text_string=welcome_private, wx_id=wx_id))
            return True
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
    return False


def add_vip(wx_id, content):
    # 添加VIP用户
    if wx_id in group_admin:
        if content.startswith(groupChatKey + "添加"):
            nick = re.sub("^" + groupChatKey + "添加", "", content, 1)
            wx_id = get_wx_id(nick)
            if user_configs.get(wx_id) is not None:
                user_configs[wx_id]['vip'] = True
                ws.send(send_txt_msg(text_string="添加成功，该用户无限制", wx_id=wx_id))
                save_config()
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
    pass


def handle_recv_txt_cite(j):
    pass


def handle_other_msg(j):
    print(j)
    json = j["content"]
    room_id = json["id1"]
    content: str = json["content"].strip()
    if content.endswith("加入了群聊"):
        nick = content.split('"邀请"')[1].split('"')[0]
        ws.send(send_txt_msg(text_string="欢迎" + nick + "入群，" + welcome_group, wx_id=room_id))
    elif content.endswith("现在可以开始聊天了。"):
        ws.send(send_txt_msg(text_string=welcome_private, wx_id=room_id))


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
websocket.enableTrace(False)
# websocket.enableTrace(True)

ws = websocket.WebSocketApp(server, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
