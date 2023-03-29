import hashlib
import json
import time
import requests

from python.basic.tools import get_now

session = requests.session()


class Xeasy:

    def __init__(self, wx_id):
        self.wx_id = wx_id

    def digest_message(self, o):
        a = o.encode()
        l = hashlib.sha256(a).digest()
        sign = ''.join(format(x, '02x') for x in l)
        return sign

    def generateSignature(self, t, m):
        M = ("%d:%s:undefined" % (t, m))
        # print("M", M)
        return self.digest_message(M)

    def ask(self, prompt):
        null = None
        t = int(time.time() * 1000)
        sign = self.generateSignature(t, prompt)
        # print("sign =", sign)
        data = {"messages": [{"role": "user", "content": prompt}], "key": null, "time": t,
                "sign": sign}
        print(get_now() + "[" + self.wx_id + "]ask：" + prompt)
        try:
            response = session.request(url="https://chat2.xeasy.me/api/generate", json=data, method="POST",
                                       timeout=120)
            reply = response.text
        except Exception as err:
            print(err)
            reply = "请求异常"
        print(get_now() + "[" + self.wx_id + "]reply：" + reply)
        return reply


if __name__ == "__main__":
    # 已证实有上下文
    test = Xeasy('test')
    test.ask("帮我描述一个图画的关键词部分，主题是：致敬英雄征文大赛海报，用英文输出")
    # test.ask("我刚才说的什么？")
