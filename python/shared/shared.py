# -*- coding: utf-8 -*-
import json
import sys
import time

# server config
with open("./config.json", encoding="utf-8") as f:
    config = json.load(f)
f.close()

# server_host = config["server_host"]
server_host = "127.0.0.1:5555"
if len(sys.argv) > 1:
    if sys.argv[1] == "2":
        server_host = "127.0.0.1:5556"
print("监听地址", server_host)
chat_interval = config["chat_interval"]

groupChatKey = config["groupChatKey"]
groupChatKey3 = config["groupChatKey3"]
groupChatKey4 = config["groupChatKey4"]
grpCitationMode = config["grpCitationMode"]
privateChatKey = config["privateChatKey"]
prvCitationMode = config["prvCitationMode"]

stableDiffRly = config["stableDiffRly"]
groupImgKey = config["groupImgKey"]
privateImgKey = config["privateImgKey"]
# 群内默认管理员ID
group_admin = config["group_admin"]

# Signal Number
RECV_TXT_CITE_MSG = 49
GET_USER_LIST_SUCCESS = 5001
ATTACH_FILE = 5003
OTHER_REQUEST = 10000

HEART_BEAT = 5005
RECV_TXT_MSG = 1
RECV_PIC_MSG = 3
USER_LIST = 5000
GET_USER_LIST_SUCCSESS = 5001
GET_USER_LIST_FAIL = 5002
TXT_MSG = 555
PIC_MSG = 500
AT_MSG = 550
CHATROOM_MEMBER = 5010
CHATROOM_MEMBER_NICK = 5020
PERSONAL_INFO = 6500
DEBUG_SWITCH = 6000
PERSONAL_DETAIL = 6550
DESTROY_ALL = 9999
NEW_FRIEND_REQUEST = 37  # 微信好友请求消息
AGREE_TO_FRIEND_REQUEST = 10000  # 同意微信好友请求消息
ATTATCH_FILE = 5003


def get_id():
    id = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))
    return id
