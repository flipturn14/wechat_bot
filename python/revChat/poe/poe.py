import datetime
import json
import logging
import os
import queue
import random
import re
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import websocket

parent_path = Path(__file__).resolve().parent
queries_path = parent_path / "poe_graphql"
queries = {}

logging.basicConfig()
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)

user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0"


def get_now():
    now = datetime.datetime.now()
    dt_string = "[" + now.strftime("%Y-%m-%d %H:%M:%S") + "]"
    return dt_string


def load_queries():
    for path in queries_path.iterdir():
        if path.suffix != ".graphql":
            continue
        with open(path) as f:
            content = f.read()
            queries[path.stem] = content
            # print(path.stem, content)


def generate_payload(query_name, variables):
    return {
        "query": queries[query_name],
        "variables": variables
    }


config_file_path = "users.json"


def configure():
    global config_file_path
    """
    Looks for a config file in the following locations:
    """
    config_files = [config_file_path]

    config_file = next((f for f in config_files if os.path.exists(f)), None)
    if config_file:
        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)
    else:
        print(get_now() + "No config file found.")
        raise Exception("No config file found.")
    # print(config)
    return config


creList: dict
creList = configure()


def request_with_retries(method, *args, **kwargs):
    attempts = kwargs.get("attempts") or 10
    url = args[0]
    for i in range(attempts):
        r = method(*args, **kwargs)
        if r.status_code == 200:
            return r
        print(
            f"Server returned a status code of {r.status_code} while downloading {url}. Retrying ({i + 1}/{attempts})...")

    raise RuntimeError(f"Failed to download {url} too many times.")


class Mail:
    BASEURL = 'https://api.guerrillamail.com/ajax.php'
    cookie = ""

    def __init__(self, wx_id):
        self.wx_id = wx_id
        self.session = requests.Session()

    def create_new_email(self):
        print(get_now() + "[" + self.wx_id + "]创建邮箱")
        response = self.session.post("https://moakt.com/zh/inbox", allow_redirects=False)
        self.cookie = "tm_session=" + response.cookies.get("tm_session")
        print("cookie=" + self.cookie)
        result = self.session.post("https://moakt.com/zh/inbox/change", headers={
            "cookie": self.cookie,
            "x-requested-with": "XMLHttpRequest"
        })
        data = json.loads(result.text)
        print("data=", data)
        email_address = data["data"]["address"]["email"]
        print(get_now() + "[" + self.wx_id + "]邮箱地址：[" + email_address + "]")
        return email_address

    def get_email_list(self):
        self.session.headers.clear()
        response = self.session.get('https://moakt.com/zh/inbox', headers={
            "cookie": self.cookie
        })
        # print("html = ", response.text)
        html = response.text
        arr = re.search(r'/(.*)">Your verification', html, re.M)
        # print(arr.group(0))
        if arr is not None:
            code = arr.group(0)[10:46]
            # print(code)
            return [code]
        else:
            return []

    def get_latest_email(self):
        # print(get_now() + "[" + self.poe_obj.wx_id + "]等待接收邮件", end='')
        while True:
            print(".", end="")
            email_list = self.get_email_list()
            email_list_length = len(email_list)
            if email_list_length > 0:
                break
            time.sleep(1.0)
        print("")
        return email_list[0]

    def get_code_id(self, id):
        url = ("https://moakt.com/zh/email/%s/content/" % id)
        # print("url = " + url)
        response = self.session.get(url, headers={
            "cookie": self.cookie
        })
        html = response.text
        # print(html)
        arr = re.search(r'\d{6}</div>', html, re.M)
        # print(arr.group(0))
        if arr is not None:
            code = arr.group(0)[0:6]
            # print(code)
            return code
        else:
            return None

    def get_poe_otp_code(self):
        print(get_now() + "[" + self.wx_id + "]获取验证码", end="")
        email_data_id = self.get_latest_email()
        code = self.get_code_id(email_data_id)
        print(get_now() + "[" + self.wx_id + "]验证码 = " + code)
        return code


sessions = {}


class Poe:
    gql_url = "https://poe.com/api/gql_POST"
    gql_recv_url = "https://poe.com/api/receive_POST"
    home_url = "https://poe.com"
    settings_url = "https://poe.com/api/settings"

    formkey = ""
    next_data = {}
    bots = {}
    active_messages = {}
    message_queues = {}
    ws = None
    ws_connected = False
    credentials = {}
    pb_cookie = None
    headers = {
        "User-Agent": user_agent,
        "Referrer": "https://poe.com/",
        "Origin": "https://poe.com",
    }

    def init(self, token, email_address=None, proxy=None):
        self.proxy = proxy
        if proxy:
            self.session.proxies = {
                "http": self.proxy,
                "https": self.proxy
            }
            print(f"Proxy enabled: {self.proxy}")
        self.session.cookies.set("p-b", token, domain="poe.com")
        self.ws_domain = f"tch{random.randint(1, 1e6)}"

        self.session.headers.update(self.headers)

        user_info = creList.get(self.wx_id)
        if user_info is None:
            creList[self.wx_id] = {
                "quora_cookie": token,
                "email_address": email_address,
            }
            data = json.dumps(creList)
            with open(config_file_path, "wb") as file_object:
                file_object.write(data.encode('utf-8'))
            file_object.close()

        self.next_data = self.get_next_data()
        self.bots = self.get_bots()
        self.bot_names = self.get_bot_names()
        self.channel = self.get_channel_data()
        self.connect_ws()
        self.gql_headers = {
            "poe-formkey": self.formkey,
            "poe-tchannel": self.channel["channel"],
        }
        self.gql_headers = {**self.gql_headers, **self.headers}
        self.subscribe()

    def __init__(self, wx_id):
        if sessions.get(wx_id) is None:
            self.session = requests.Session()
            sessions[wx_id] = self.session
        else:
            self.session = sessions[wx_id]
        self.gql_headers = {}
        self.wx_id = wx_id
        user_info = creList.get(wx_id)
        if user_info is None:
            print("%s cookie is None,创建账号" % wx_id)
            cookie = self.set_credentials()
            email_address = self.login()
            print(get_now() + "[" + self.wx_id + "]证书写入文件")
            self.init(self.pb_cookie, email_address)
        else:
            self.pb_cookie = user_info['quora_cookie']
            # print("%s cookie = %s" % (wx_id, self.pb_cookie))
            self.init(self.pb_cookie)

    def get_next_data(self):
        print("Downloading next_data...")

        r = request_with_retries(self.session.get, self.home_url)
        json_regex = r'<script id="__NEXT_DATA__" type="application\/json">(.+?)</script>'
        json_text = re.search(json_regex, r.text).group(1)
        next_data = json.loads(json_text)

        self.formkey = next_data["props"]["formkey"]
        self.viewer = next_data["props"]["pageProps"]["payload"]["viewer"]

        return next_data

    def get_bots(self):
        print("get bots")
        viewer = self.next_data["props"]["pageProps"]["payload"]["viewer"]
        if not "availableBots" in viewer:
            raise RuntimeError("Invalid token.")
        bot_list = viewer["availableBots"]

        bots = {}
        for bot in bot_list:
            if bot["displayName"].lower() == "chatgpt":
                url = f'https://poe.com/_next/data/{self.next_data["buildId"]}/{bot["displayName"].lower()}.json'
                print("Downloading " + url)

                r = request_with_retries(self.session.get, url)

                chat_data = r.json()["pageProps"]["payload"]["chatOfBotDisplayName"]
                bots[chat_data["defaultBotObject"]["nickname"]] = chat_data

        return bots

    def get_bot_names(self):
        bot_names = {}
        for bot_nickname in self.bots:
            bot_obj = self.bots[bot_nickname]["defaultBotObject"]
            bot_names[bot_nickname] = bot_obj["displayName"]
        return bot_names

    def get_channel_data(self, channel=None):
        print(get_now() + "[" + self.wx_id + "]Downloading channel data...")
        r = request_with_retries(self.session.get, self.settings_url)
        data = r.json()

        self.formkey = data["formkey"]
        return data["tchannelData"]

    def get_websocket_url(self, channel=None):
        if channel is None:
            channel = self.channel
        query = f'?min_seq={channel["minSeq"]}&channel={channel["channel"]}&hash={channel["channelHash"]}'
        return f'wss://{self.ws_domain}.tch.{channel["baseHost"]}/up/{channel["boxName"]}/updates' + query

    def send_query(self, query_name, variables):
        for i in range(20):
            payload = generate_payload(query_name, variables)
            # print(json.dumps(payload))
            r = request_with_retries(self.session.post, self.gql_url, json=payload, headers=self.gql_headers)
            data = r.json()
            if data["data"] == None:
                print(f'{query_name} returned an error: {data["errors"][0]["message"]} | Retrying ({i + 1}/20)')
                time.sleep(2)
                continue

            return r.json()

    def subscribe(self):
        print("Subscribing to mutations")
        result = self.send_query("SubscriptionsMutation", {
            "subscriptions": [
                {
                    "subscriptionName": "messageAdded",
                    "query": queries["MessageAddedSubscription"]
                },
                {
                    "subscriptionName": "viewerStateUpdated",
                    "query": queries["ViewerStateUpdatedSubscription"]
                }
            ]
        })

    def ws_run_thread(self):
        kwargs = {}
        if self.proxy:
            proxy_parsed = urlparse(self.proxy)
            kwargs = {
                "proxy_type": proxy_parsed.scheme,
                "http_proxy_host": proxy_parsed.hostname,
                "http_proxy_port": proxy_parsed.port
            }

        self.ws.run_forever(**kwargs)

    def connect_ws(self):
        self.ws = websocket.WebSocketApp(
            self.get_websocket_url(),
            header={"User-Agent": user_agent},
            on_message=self.on_message,
            on_open=self.on_ws_connect,
            on_error=self.on_ws_error
        )
        t = threading.Thread(target=self.ws_run_thread, daemon=True)
        t.start()
        while not self.ws_connected:
            time.sleep(0.01)

    def disconnect_ws(self):
        if self.ws:
            self.ws.close()
        self.ws_connected = False

    def on_ws_connect(self, ws):
        self.ws_connected = True

    def on_ws_error(self, ws, error):
        print(f"Websocket returned error: {error}")
        self.disconnect_ws()
        self.connect_ws()

    def on_message(self, ws, msg):
        data = json.loads(msg)
        try:
            message = json.loads(data["messages"][0])["payload"]["data"]["messageAdded"]

            copied_dict = self.active_messages.copy()
            for key, value in copied_dict.items():
                # add the message to the appropriate queue
                if value == message["messageId"] and key in self.message_queues:
                    self.message_queues[key].put(message)
                    return
                # indicate that the response id is tied to the human message id
                elif key != "pending" and value is None and message["state"] != "complete":
                    self.active_messages[key] = message["messageId"]
                    self.message_queues[key].put(message)
        except Exception as err:
            print(err, msg)
            self.disconnect_ws()
            self.connect_ws()

    def send_message(self, chatbot, message, with_chat_break=False, timeout=20):
        # if there is another active message, wait until it has finished sending
        while None in self.active_messages.values():
            time.sleep(0.01)

        # None indicates that a message is still in progress
        self.active_messages["pending"] = None

        print(get_now() + "[" + self.wx_id + "]" + f"Sending message to {chatbot}: {message}")

        message_data = self.send_query("AddHumanMessageMutation", {
            "bot": chatbot,
            "query": message,
            "chatId": self.bots[chatbot]["chatId"],
            "source": None,
            "withChatBreak": with_chat_break
        })
        del self.active_messages["pending"]

        if not message_data["data"]["messageCreateWithStatus"]["messageLimit"]["canSend"]:
            raise RuntimeError(f"Daily limit reached for {chatbot}.")
        try:
            human_message = message_data["data"]["messageCreateWithStatus"]
            human_message_id = human_message["message"]["messageId"]
        except TypeError:
            raise RuntimeError(f"An unknown error occured. Raw response data: {message_data}")

        # indicate that the current message is waiting for a response
        self.active_messages[human_message_id] = None
        self.message_queues[human_message_id] = queue.Queue()

        last_text = ""
        message_id = None
        while True:
            try:
                message = self.message_queues[human_message_id].get(timeout=timeout)
            except queue.Empty:
                del self.active_messages[human_message_id]
                del self.message_queues[human_message_id]
                # raise RuntimeError("Response timed out.")
                message["text"] = "请求超时，请重试"
                break

            # only break when the message is marked as complete
            if message["state"] == "complete":
                if last_text and message["messageId"] == message_id:
                    break
                else:
                    continue

            # update info about response
            message["text_new"] = message["text"][len(last_text):]
            last_text = message["text"]
            message_id = message["messageId"]

            yield message

        del self.active_messages[human_message_id]
        del self.message_queues[human_message_id]

    def send_chat_break(self, chatbot):
        print(f"Sending chat break to {chatbot}")
        result = self.send_query("AddMessageBreakMutation", {
            "chatId": self.bots[chatbot]["chatId"]
        })
        return result["data"]["messageBreakCreate"]["message"]

    def get_message_history(self, chatbot, count=25, cursor=None):
        print(f"Downloading {count} messages from {chatbot}")
        result = self.send_query("ChatListPaginationQuery", {
            "count": count,
            "cursor": cursor,
            "id": self.bots[chatbot]["id"]
        })
        return result["data"]["node"]["messagesConnection"]["edges"]

    def delete_message(self, message_ids):
        print(f"Deleting messages: {message_ids}")
        if not type(message_ids) is list:
            message_ids = [int(message_ids)]

        result = self.send_query("DeleteMessageMutation", {
            "messageIds": message_ids
        })

    def purge_conversation(self, chatbot, count=-1):
        # print(f"Purging messages from {chatbot}")
        last_messages = self.get_message_history(chatbot, count=50)[::-1]
        while last_messages:
            message_ids = []
            for message in last_messages:
                if count == 0:
                    break
                count -= 1
                message_ids.append(message["node"]["messageId"])

            self.delete_message(message_ids)

            if count == 0:
                return
            last_messages = self.get_message_history(chatbot, count=50)[::-1]
        # print(f"No more messages left to delete.")

    def set_credentials(self):
        print(get_now() + "[" + self.wx_id + "]设置证书")
        app_settings = self.scrape()
        # set value
        self.gql_headers["poe-formkey"] = app_settings["formkey"]
        self.gql_headers["poe-tchannel"] = app_settings["tchannelData"]["channel"]
        self.gql_headers["Cookie"] = "p-b=" + self.pb_cookie
        self.gql_headers = {**self.gql_headers, **self.headers}
        self.session.headers.update(self.gql_headers)
        # print("set header ", self.gql_headers)
        self.credentials["quora_cookie"] = self.pb_cookie
        return self.pb_cookie

    def scrape(self):
        print(get_now() + "[" + self.wx_id + "]获取页面信息")
        response = self.session.get("https://poe.com/login")
        # print(self.session.headers, self.session.cookies.get_dict())
        cookie = response.cookies.get("p-b")
        self.pb_cookie = cookie
        self.session.headers.update(self.gql_headers)
        self.session.cookies.set("p-b", self.pb_cookie, domain="poe.com")
        print(get_now() + "[" + self.wx_id + "]获取settings")
        _setting = self.session.get('https://poe.com/api/settings')
        # print(self.session.headers)
        # print(get_now() + "[" + self.wx_id + "]settings = " + _setting.text)
        app_settings = json.loads(_setting.text)
        return app_settings

    def login(self):
        print(get_now() + "[" + self.wx_id + "]准备登录")
        mail = Mail(self.wx_id)
        email_address = mail.create_new_email()
        status = self.send_verif_code(email_address)
        print(get_now() + "Waiting for OTP code...")
        otp_code = mail.get_poe_otp_code()
        if status == 'user_with_confirmed_email_not_found':
            self.sign_up_with_verification_code(email_address, otp_code)
        else:
            self.sign_in_or_up(email_address, otp_code)
        return email_address

    def get_updated_settings(self, channel_name, pb_cookie):
        print(get_now() + "[" + self.wx_id + "]更新设置")
        headers = {"cookie": pb_cookie}
        url = "https://poe.com/api/settings?channel=%s" % channel_name
        # print(get_now() + "[" + self.wx_id + "]url = " + url)
        response = self.session.get(url, data=None, headers=headers)
        print(get_now() + "[" + self.wx_id + "]更新设置返回结果" + response.text)
        credentials = json.loads(response.text)
        creList[self.wx_id] = credentials
        data = json.dumps(creList)
        with open(config_file_path, "wb") as file_object:
            file_object.write(data.encode('utf-8'))
        file_object.close()
        min_seq = credentials["tchannelData"]["minSeq"]
        return min_seq

    def send_verif_code(self, email):
        print(get_now() + "[" + self.wx_id + "]请求验证码")
        null = None
        result = self.send_query("SendVerificationCodeForLoginMutation", {
            "emailAddress": email,
            "phoneNumber": null
        })
        # print(result)
        status = result["data"]["sendVerificationCode"]["status"]
        print(get_now() + "Verification code sent. Status: " + status)
        return status

    def sign_up_with_verification_code(self, email, verify_code):
        print(get_now() + "[" + self.wx_id + "]登录验证Email: " + email + " Verification code: " + verify_code)
        null = None
        result = self.send_query("signup", {
            "verificationCode": verify_code,
            "emailAddress": email,
            "phoneNumber": null
        })
        # print("result = " , result)
        login_status = result["data"]["signupWithVerificationCode"]["status"]
        print(get_now() + "[" + self.wx_id + "]Login Status: " + login_status)
        return login_status

    def sign_in_or_up(self, email, verify_code):
        print(get_now() + "[" + self.wx_id + "]登录验证Email: " + email + "Verification code: " + verify_code)
        result = self.send_query("signUpWithVerificationCodeMutation", {
            "verificationCode": verify_code,
            "emailAddress": email
        })
        result = json.loads(result)
        login_status = result["data"]["loginWithVerificationCode"]["status"]
        print(get_now() + "[" + self.wx_id + "]Login Status: " + login_status)
        return login_status

    def ask(self, prompt):
        print(get_now() + "[" + self.wx_id + "]ask：" + prompt)
        self.content = prompt
        if prompt:
            result = ""
            for chunk in self.send_message("chinchilla", prompt):
                # print(chunk["text_new"], end="", flush=True)
                # result += chunk["text_new"]
                result = chunk["text"]
            # print(get_now() + "Response: ")
            # self.purge_conversation("chinchilla", count=3)
            return result


load_queries()

if __name__ == "__main1__":
    mail = Mail("suleil1")
    # email_address = mail.create_new_email()
    mail.get_poe_otp_code()

if __name__ == "__main__":
    client = Poe("suleil2")
    message = "你是谁"
    print(client.ask(message))
