from steamship import Steamship

from python.basic.tools import get_now


class Gpt4:
    client = Steamship(workspace="my-unique-name")
    generator = client.use_plugin('gpt-4', config={"max_tokens": 8000})

    def __init__(self, wx_id):
        self.wx_id = wx_id

    def ask(self, prompt):
        print(get_now() + "[" + self.wx_id + "]ask：" + prompt)
        try:
            task = self.generator.generate(text=prompt)
            task.wait()
            reply = task.output.blocks[0].text
        except Exception as err:
            print(err)
            reply = "请求异常"
        print(get_now() + "[" + self.wx_id + "]reply：" + reply)
        return reply


if __name__ == "__main__":
    # 已测试没有上下文，需要自己实现上下文
    gpt4 = Gpt4("test")
    gpt4.ask("你有上下文关联吗？")
    gpt4.ask("我上一句说的什么？")
