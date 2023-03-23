import os.path
import random
import string
import threading

import requests

from python.shared.shared import *
from .send import send_txt_msg, send_pic_msg
from .tools import get_now, translate

global_wx_dict = dict()


class ChatTask(threading.Thread):
    def __init__(self, ws, prompt, chatbot, wx_id, room_id, is_room, is_citation):
        super(ChatTask, self).__init__()
        self.ws = ws
        self.prompt = prompt.strip()
        self.bot = chatbot
        self.wx_id = wx_id
        self.room_id = room_id
        self.is_room = is_room
        self.is_citation = is_citation

    def run(self):
        if self.prompt is None or self.prompt == "":
            print("消息为空，直接返回")
            return
        start_time = time.time()
        reply = self.bot.ask(prompt=self.prompt)
        run_time = time.time() - start_time
        hs = "耗时：" + str(run_time) + "秒"
        print(get_now() + hs)
        if self.is_citation:
            reply = global_wx_dict[self.wx_id] + "：" + self.prompt + \
                    "\n--------------------\n" + reply.strip()
        self.ws.send(
            send_txt_msg(text_string=reply.strip() + "\n--------------------\n" + hs,
                         wx_id=self.room_id if self.is_room else self.wx_id))


class ImgTask:
    def __init__(self, ws, prompt, wx_id, room_id, is_room):
        self.ws = ws
        self.prompt = prompt
        self.wx_id = wx_id
        self.room_id = room_id
        self.is_room = is_room

    def start(self):
        self.get_img()

    def get_img(self):
        task_name = 'task(' + ''.join(random.sample(string.ascii_letters + string.digits, 15)) + ')'
        session_hash = ''.join(random.sample(string.ascii_letters + string.digits, 11))
        url = 'http://127.0.0.1:7860/run/predict/'
        keys = self.prompt.split("/")
        # forward = "(masterpiece),(8k, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), ultra-detailed," + keys[0]
        forward = keys[0]
        reverse = ""
        # reverse = "paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, (outdoor:1.6),  backlight,(ugly:1.331), (duplicate:1.331), (morbid:1.21), (mutilated:1.21), (tranny:1.331), mutated hands, (poorly drawn hands:1.331), blurry, (bad anatomy:1.21), (bad proportions:1.331), extra limbs, (disfigured:1.331), (more than 2 nipples:1.331), (missing arms:1.331), (extra legs:1.331), (fused fingers:1.61051), (too many fingers:1.61051), (unclear eyes:1.331), bad hands, missing fingers, extra digit, (futa:1.1), bad body, NG_DeepNegative_V1_75T,pubic hair, glans"
        if len(keys) > 1:
            reverse = keys[1]
        s = "".join(['{"fn_index": 122,',
                     '"data": ["' + task_name +
                     '", "' +
                     translate(forward) + '", "' +  # 正向词
                     translate(reverse) +  # 反向词
                     '", [], 20, "DPM++ 2M Karras",'
                     ' false, false, 1, 1, 7.5,'
                     ' 1946337970, -1,',
                     '0, 0, 0, false, 768, 512, true, 0.7, 2,'
                     ' "Latent", '
                     '0, 0, 0, [], '
                     '"None", false, false,',
                     '"LoRA", "None", 1, 1, "LoRA", "None", 1, 1, "LoRA", "None", 1, 1, '
                     '"LoRA", "None", 1, 1, "LoRA", "None", 1, 1, "Refresh models",'
                     ' false, "none", "None", 1, null, false,',
                     '"Scale to Fit (Inner Fit)", false, false, 64, 64, 64, 1, false, false, false,',
                     '"positive", "comma", 0, false, false, "", "Seed", "", "Nothing", "", "Nothing", "",',
                     'true, false, false, false, 0, [], "", "", ""], "session_hash": "' + session_hash + '"}'])
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        print("param = " + s)
        print("生成图片")
        start_time = time.time()
        message = requests.post(url, data=s.encode("utf-8"), headers=headers)
        print("生成结束")
        print("message = " + message.text)
        msg = json.loads(message.text)
        for item in msg["data"][0]:
            run_time = time.time() - start_time
            hs = "耗时：" + str(run_time) + "秒"
            self.ws.send(send_pic_msg(wx_id=self.room_id if self.is_room else self.wx_id,
                                      content=item['name']))
            self.ws.send(
                send_txt_msg(text_string=global_wx_dict[
                                             self.wx_id] + "：" + self.prompt.strip() + "\n--------------------\n" + hs,
                             wx_id=self.room_id if self.is_room else self.wx_id))
            time.sleep(1.0)
            # 删除源文件节省空间
            os.remove(item['name'])
