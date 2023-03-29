import requests
from urllib3 import disable_warnings

disable_warnings()

from python.basic.tools import get_now


class YQcloud:

    def __init__(self, wx_id):
        self.wx_id = wx_id
        self.session = requests.session()

    def ask(self, prompt):
        true = True
        data = {"prompt": prompt, "userId": "#/chat/" + self.wx_id, "network": true}
        print(get_now() + "[" + self.wx_id + "]ask：" + prompt)
        try:
            response = self.session.request(url="https://cbjtestapi.binjie.site:7777/api/generateStream", json=data,
                                            method="POST", timeout=120, verify=False, headers={
                    "origin": "https://dev.yqcloud.top",
                    "referer": "https://dev.yqcloud.top/",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
                })
            reply = response.text
            print("reply = " + reply)
            content_arr = reply.split("\n")
            if len(content_arr) > 1:
                reply = content_arr[2]
        except Exception as err:
            print(err)
            reply = "请求异常"
        print(get_now() + "[" + self.wx_id + "]reply：" + reply)
        return reply


if __name__ == "__main__":
    # 已证实有上下文
    test = YQcloud('test')
    test.ask("记住我刚才说的这句话")
    test.ask("我刚才说的什么？")
