import threading
import queue

chat_que = queue.Queue()
img_que = queue.Queue()


class Processor(threading.Thread):

    def __init__(self, que):
        super(Processor, self).__init__()
        self.que: queue.Queue = que
        self.daemon = True
        self.start()

    def run(self):
        while True:
            item = self.que.get()
            # 增加异常处理避免退出
            try:
                item.start()
            except Exception as err:
                print(err)
            del item
            # item.start()
            # del item
