import requests
import json

# API的URL
url = 'http://localhost:11434/api/chat'
input_text = "穿山甲（汤浸透，取甲锉碎，同热灰铛内慢火炒令黄色）五钱  红色曲（炒）  川乌（一枚，灰火中带焦炮）各二钱半"

# 要发送的数据
data = {
    "model": "llama3.2",
    "messages": [
        {"role":"system","content": "你是一个中药药材提取工具，只知道药材名字，你的工作是从字符串中提取药材名字，并用英文逗号隔开。"},
        {"role": "user","content": " "}
    ],
    "stream": False
}

# 找到role为user的message
for message in data["messages"]:
    if message["role"] == "user":
        # 将输入文本添加到content的开头
        message["content"] = input_text

# 将字典转换为JSON格式的字符串
json_data = json.dumps(data)

# 发送POST请求
response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})

# 打印响应内容
print(response.text)
