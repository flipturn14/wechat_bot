import datetime
import deepl


def get_now():
    now = datetime.datetime.now()
    dt_string = "[" + now.strftime("%Y-%m-%d %H:%M:%S") + "]"
    return dt_string


def translate(text):
    """
    转换中文为英文
    :param text: 字符串
    :return: 转换完成的文本
    """
    if is_chinese(text):
        try:
            return deepl.translate(source_language="ZH", target_language="EN", text=text)
        except Exception as err:
            print(err)
            return text
    else:
        return text


def is_chinese(string):
    """
    判断是否有中文
    :param string:  来源
    :return: 存在中文返回true
    """
    for chart in string:
        if b'\xb0\xa1' <= chart.encode("gb2312") <= b'\xd7\xf9':
            return True
    return False


if __name__ == "__main__":
    # print(translate("Hello, I need some help, can I"))
    print(is_chinese("Hello, I need some help, can I"))
