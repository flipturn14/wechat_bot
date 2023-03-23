import requests

from python.basic.tools import get_now


class Poe:

    def __init__(self, wx_id):
        self.wx_id = wx_id

    def ask(self, prompt):
        data = {
            "content": prompt,
            "wx_id": self.wx_id
        }
        print(get_now() + "[" + self.wx_id + "]ask：" + prompt)
        try:
            response = requests.request(url="http://localhost:8080", json=data, method="POST", timeout=90)
            reply = response.text
        except Exception as err:
            print(err)
            reply = "请求异常"
        print(get_now() + "[" + self.wx_id + "]reply：" + reply)
        return reply


if __name__ == "__main__":
    # 已证实有上下文
    poe = Poe('test')
    poe.ask("请记住我刚才说的话")
    poe.ask("我刚才说的什么？")
