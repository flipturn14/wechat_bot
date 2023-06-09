<h1 align="center">wechat_bot</h1>




使用基于 ChatGPT (非API-KEY调用) 、Stable Diffusion AI画图（需要自己本地部署） 与 官方微信hook接口 的 ChatGPT-3 / ChatGPT4
机器人。（本着开源想法，连Readme都是抄的）

私聊加好友后默认不开启，对话会进行提示

入群新人会自动欢迎。

###### 作者

[FlipTurn (github.com)](https://github.com/flipturn14)

## 支持和特点

- [x] 支持多线程对话
- [x] ChatGPT-3支持上下文问答
- [x] 支持多线程 `Stable Diffusion` AI 画图功能，（需自己搭建，中文自动转换为英文）
- [x] **使用官方微信软件执行，信息来源方面永不封禁**（据说）
- [x] **同时使用人数过多，会被封号，我刚被封一个月**
- [x] 设置关键字在群聊中唤醒微信机器人
- [x] 设置关键字以重置之前的对话
- [x] 重新生成答案
- [x] 回滚对话

## 默认配置 （请在启动前仔细阅读，所有配置文件在config.json中）

```
{
  // 本地host运行地址（仅本地）
  "server_host": "127.0.0.1:5555",
  //两次聊天间隔时间
  "chat_interval": 120,

  // 在群聊中设置唤醒ChatGPT-3关键词
  "groupChatKey": "g",
  // 在群聊中设置唤醒ChatGPT-4关键词
  "groupChatKey": "c",
  // 在群聊回答前添加源问题格式
  "grpCitationMode": true,
  // 在私聊中设置唤醒机器人关键词，为空时所有都回答
  "privateChatKey": "",
  // 在群聊回答前添加源问题格式
  "prvCitationMode": false,
  // 群聊的管理员，可以使用群聊唤醒关键词加启用来启动群聊，群聊唤醒关键词加关闭来关闭群聊，避免刷屏
  "group_admin": ["admin1","admin2"],
  
  // 是否开启 Stable Diffusion 图片回复
  "stableDiffRly": true,
  // 在群聊中设置唤醒 AI画图功能关键词
  "groupImgKey": "t",
  // 在私聊中设置唤醒 AI画图功能关键词
  "privateImgKey": "t",
}
```

## 启动步骤

1. 安装 `requirements.txt` 中列出的所有包，使用如下命令：

   ```
   pip install -r ./requirements.txt
   ```

2. 在您的计算机上安装 `WeChat-3.6.0.18.exe`，**如果您正在使用的微信版本高于3.6.0.18，可以降级覆盖安装。**
   之后请登陆您的微信。**

3. 运行服务器监控微信消息。这里有两种方法可以实现，请 ***二选一***：

    - 打开名字为 `tools/DLLinjector_V1.0.3.exe` 的注入器，然后选择文件名为 `3.6.0.18-0.0.0.008.dll` 并注入。

      ![image-20230221044543472](assets/image-20230221044543472.png)

    - 运行 `funtool_3.6.0.18-1.0.0013.exe` ，后点击 `Start` 。

      ![image-20230221044609319](assets/image-20230221044609319.png)

4. 双开时打开一个微信登录后，打开微信DLL注入器点击注入，再打开一个微信后使用FunTool修改端口后点击Start

5. 需要在 `config.json` 目录下填写 JSON 文件，您需要根据自己的偏好配置自定义选项。

6. 切换至根目录，运行以下命令启动服务：

   ```
   python main.py
   ```


**一切准备就绪，欢迎使用 Wechat_bot！**

**没有限制、没有使用计数，也没有付费要求。** 

需要科学上网，自动生成邮箱登录Poe进行对话。

需要生成图片请自行安装webui并下载各种模型后启动，此处不进行讲解。

## 常见问题解答

1. 遇到问题了吗？随时来创建一个 issue 进行发布。
2. 如何才能在多线程的程序中定位问题？使用 print 或使用debug工具查看线程栈信息
3. 是否有一些功能预览的图片？没有，被我删掉了
4. 要请我喝咖啡吗？谢谢，请不要花太多钱。
5. 支付宝
   ![image-20230221044543472](assets/zfb.png)
6. 微信
   ![image-20230221044543472](assets/wx.png)

## 日志
- 2023年4月02日
1. 恢复使用Poe，修改为Python版本，并会自动进行注册
2. 增加多个对话对接地址
- 2023年3月24日
1. 增加对话时间间隔限制，避免同时聊天人数过多，配置文件新增`chat_interval`配置项，适用于群聊和私聊
2. 增加管理员功能，配置文件中增加管理员，管理员可使用命令[关键词]添加[昵称]来增加VIP人员，该人员不受时间间隔限制，或使用命令[关键词]删除[昵称]来增加VIP人员，该人员受到时间间隔限制。举例：g添加FlipTurn
3. 拆分函数

- 2023年3月23日

1. 增加配置文件，默认私聊关闭自动回复。可输入命令`启用/关闭/帮助` 群聊可输入`g启用/g关闭`进行控制；
2. 增加私聊间隔时长避免封号；
3. 增加VIP功能，可输入关键词加添加wx_id 让用户无间隔限制；输入关键词加删除wx_id让用户受间隔限制；

- 2023年3月22日 公布版本

###### 参考

- [https://github.com/SnapdragonLee/ChatGPT-weBot](https://github.com/SnapdragonLee/ChatGPT-weBot)
- [https://github.com/muharamdani/poe](https://github.com/muharamdani/poe)
- [https://github.com/ading2210/poe-api](https://github.com/ading2210/poe-api)
