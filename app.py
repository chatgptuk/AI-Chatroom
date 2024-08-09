from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import openai
from openai import OpenAI
import random
import uuid
import re
from datetime import datetime, timedelta
from pytz import timezone
import pytz
import json
import requests
import base64
# 为Flask应用配置一个秘密密钥，用于保护会话数据
app = Flask(__name__)
app.secret_key = ''
app.config['SESSION_TYPE'] = 'filesystem'

socketio = SocketIO(app, cors_allowed_origins="*")
client = OpenAI(
    base_url="https://api.openai.com/v1",
    api_key="sk-xxxx"
)

users = {}
user_ips = {}
conversations = {}
first_time_users = {}
last_message_times = {}
username_changes = {}
muted_users = set()
message_times = {}
uuid_mapping = {}
animals = [
    '晨曦', '晓月', '彦泽', '思远', '韵寒', '浩然', '子墨', '紫烟', '雨珍', '清雅',
    '静宸', '千羽', '梦琪', '忆柳', '之桃', '慕青', '问兰', '尔岚', '元香', '初夏',
    '沛菡', '傲珊', '曼文', '乐菱', '痴珊', '恨玉', '惜文', '香寒', '新柔', '语蓉',
    '海安', '夜蓉', '涵柏', '水桃', '醉蓝', '春儿', '语琴', '从彤', '傲晴', '语兰',
    '又菱', '碧彤', '元霜', '怜梦', '紫寒', '妙彤', '曼易', '南莲', '紫翠', '雨寒',
    '易烟', '如萱', '若南', '寻真', '晓亦', '向珊', '慕灵', '以蕊', '寻雁', '映易',
    '雪柳', '孤岚', '笑霜', '海云', '凝天', '沛珊', '寒云', '冰旋', '宛儿', '绿真',
    '晓霜', '碧凡', '夏菡', '曼香', '若烟', '半梦', '雅绿', '冰蓝', '灵槐', '平安',
    '书翠', '翠风', '香巧', '代云', '梦曼', '幼翠', '友安', '听枫', '夜绿', '雪莲',
    '从丹', '忆秋', '寄瑶', '绮山', '雁蓉', '冷霜', '灵萱', '向松', '惜寒', '紫安'
]
adjectives = [
    '王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴',
    '徐', '孙', '马', '朱', '胡', '郭', '何', '高', '林', '罗',
    '郑', '梁', '谢', '宋', '唐', '许', '邓', '冯', '韩', '曹',
    '曾', '彭', '萧', '蔡', '潘', '田', '董', '袁', '于', '余',
    '叶', '蒋', '杜', '苏', '魏', '程', '吕', '丁', '沈', '任',
    '姚', '卢', '傅', '钟', '姜', '崔', '谭', '廖', '范', '汪',
    '陆', '金', '石', '戴', '贾', '韦', '夏', '邱', '方', '侯',
    '邹', '熊', '孟', '秦', '白', '江', '阎', '薛', '尹', '段',
    '雷', '黎', '史', '龙', '陶', '贺', '顾', '毛', '郝', '龚',
    '邵', '万', '钱', '严', '覃', '武', '戚', '莫', '孔', '向'
]

def load_banned_words():
    try:
        with open('static/banned_words.txt', 'r', encoding='utf-8') as file:
            banned_words = [line.strip() for line in file.readlines()]
        return banned_words
    except Exception as e:
        print(f"Error loading banned words: {e}")
        return []
        
def get_ip_geolocation(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?lang=zh-CN')
        if response.status_code == 200:
            data = response.json()
            return f"{data['city']}, {data['regionName']}, {data['country']}"
        else:
            return "Location not available"
    except Exception as e:
        return "Error fetching location"

@app.route('/')
def index():
    return render_template('index.html', server_time=datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S'))

@socketio.on('connect')
def connect():
    # 获取查询参数中的用户名
    username = request.args.get('username')
    user_id = request.sid
    users[user_id] = username
    user_uuid = request.args.get('userId')  # 获取 UUID
    
    # 保存连接用户的 IP 地址
    user_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
    user_ips[user_id] = user_ip
    # 将 user_id 和 UUID 关联起来
    uuid_mapping[user_id] = user_uuid
    
    # 初始化或更新用户的更改次数记录
    if user_uuid not in username_changes:
        username_changes[user_uuid] = []

    # 如果没有提供用户名或者用户名不合法，则生成一个新的用户名
    if not username or not re.match(r'^[a-zA-Z\u4e00-\u9fa5]{1,20}$', username) or username.lower() in ['admin', 'chatgpt', 'undefined', 'administrator']:
        username = random.choice(adjectives) + random.choice(animals)

    # 检查用户名是否符合要求
    if not re.match(r'^[a-zA-Z\u4e00-\u9fa5]{1,20}$', username) or username.lower() in ['admin', 'chatgpt', 'undefined', 'administrator']:
        emit('message', {'user': 'admin', 'text': 'Username is invalid. It should only contain English letters, Chinese characters, should not exceed 20 characters, and should not be "admin" or "ChatGPT".'}, room=request.sid)
        return
    # 检查用户名是否已被其他会话占用
    current_sid = request.sid
    if any(sid != current_sid and users[sid] == username for sid in users):
        username = random.choice(adjectives) + random.choice(animals)
        while any(sid != current_sid and users[sid] == username for sid in users):
            username = random.choice(adjectives) + random.choice(animals)

    users[request.sid] = username
    conversations[request.sid] = []

    # 如果用户是第一次连接，那么就发送他们的加入消息
    if username not in first_time_users:
        first_time_users[username] = True
        now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        additional_links = (
            '个人网站：<br>'
            '<a href="https://www.chatgpt.org.uk/" target="_blank">https://www.chatgpt.org.uk/</a><br>'
        )
        welcome_message = (
            f'<strong>admin</strong>: {username}, welcome to the chat. '
            'Please @ChatGPT to get responses. Do not send spam messages. '
            f'{username}，欢迎加入聊天室。'
            '你可以@ChatGPT来获取回复，请勿发送垃圾信息或刷屏。'
            'Telegram交流群如下：<br>'
            '<img src="/static/telegram-group.jpg" alt="Telegram Group" width="300px" height="auto"><br>'
            f'{additional_links}'
        )
        emit('message', {'user': 'admin', 'text': welcome_message, 'timestamp': now}, room=request.sid)


    emit('onlineUsers', users, broadcast=True)
    emit('username', username)  # 发送用户名
    
@socketio.on('disconnect')
def disconnect():
    user = users[request.sid]
    del users[request.sid]
    if request.sid in conversations:
        del conversations[request.sid]
    emit('onlineUsers', users, broadcast=True)

@socketio.on('clearHistory')
def clear_history():
    if request.sid in conversations:
        conversations[request.sid] = []


@socketio.on('changeUsername')
def change_username(new_username):
    # 检查新用户名是否符合要求
    if not re.match(r'^[a-zA-Z\u4e00-\u9fa5]{1,20}$', new_username) or new_username.lower() in ['admin', 'chatgpt', 'undefined', 'administrator']:
        emit('message', {'user': 'admin', 'text': 'Username is invalid. It should only contain English letters, numbers, Chinese characters, should not exceed 20 characters, and should not be reserved words.'}, room=request.sid)
        return
    current_sid = request.sid
    # 检查新用户名是否已被其他会话占用
    if any(sid != current_sid and users[sid] == new_username for sid in users):
        emit('message', {'user': 'admin', 'text': 'Username is already taken. Please choose a different one.'}, room=request.sid)
        return

    # 检查用户是否已经达到每日更改限制
    user_id = request.sid
    user_uuid = uuid_mapping.get(user_id)
    changes = username_changes.get(user_uuid, [])
    if len(changes) >= 2 and changes[-1].date() == datetime.now().date():
        # 向用户发送超过更改次数的消息
        emit('message', {'user': 'admin', 'text': 'You can only change your username twice per day.'}, room=user_id)
        # 确保发送回前端的是当前的用户名，而不是尝试更改的新用户名
        current_username = users.get(user_id, "Unknown User")
        emit('username', current_username, room=user_id)
        return

    # 更新用户名更改信息
    changes.append(datetime.now())
    username_changes[user_uuid] = changes

    # 更改用户名
    users[user_id] = new_username

    # 更新客户端的用户名
    emit('username', new_username, room=request.sid)
    emit('onlineUsers', users, broadcast=True)

@socketio.on('sendMessage')
def handle_message(data):
    user = users[request.sid]
    message = data['message']
    model_str = data.get('model', 'gpt-3.5-turbo')

    # 加载禁用词列表
    banned_words = load_banned_words()

    # 检查消息是否包含禁止的字符串
    if any(banned_word in message for banned_word in banned_words):
        emit('message', {'user': 'admin', 'text': f'<strong>admin</strong>: @{user}, your message contains a forbidden string.'}, room=request.sid)
        return
    # 检查消息是否以 神秘字符串"sendtoall" 开头
    if message.startswith('sendtoall'):
        try:
            message = message.replace('<br>@ChatGPT', '')
            # 提取要广播的系统消息内容
            _, system_message = message.split('+', 1)
            now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
            broadcast_message = f'<strong>admin</strong>: {system_message}'

            # 向所有在线用户广播系统消息
            emit('message', {'user': 'admin', 'text': broadcast_message, 'timestamp': now}, broadcast=True)
        except ValueError:
            # 如果解析字符串失败，通知发送者
            emit('message', {'user': 'admin', 'text': f'<strong>admin</strong>: Error parsing broadcast command.', 'timestamp': now}, room=request.sid)
        return
    
    now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
    # 检查用户是否在过去的20秒内已经发送过一条消息
    if user in last_message_times and datetime.now() - last_message_times[user] < timedelta(seconds=20):
        emit('message', {'user': 'admin', 'text': f'<strong>admin</strong>: @{user}, you are sending messages too frequently. Please wait for a few seconds and try again.','timestamp': now}, room=request.sid)
        return
    # 特定神秘字符串的格式为 "send"+"用户名"+"系统消息"
    if message.startswith('send+'):
        try:
            message = message.replace('<br>@ChatGPT', '')
            _, target_username, system_message = message.split('+', 2)
            # 检查目标用户名是否存在于在线用户列表中
            if any(u == target_username for u in users.values()):
                # 找到目标用户的SID
                target_sid = [sid for sid, u in users.items() if u == target_username][0]
                # 向目标用户发送系统消息
                now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
                emit('message', {'user': 'admin', 'text': f'<strong>admin</strong>: {system_message}', 'timestamp': now}, room=target_sid)

                # 向发送者提供成功发送的反馈
                emit('message', {'user': 'admin', 'text': f'<strong>admin</strong>: Message sent to {target_username}.', 'timestamp': now}, room=request.sid)
            else:
                # 如果目标用户不在线，通知发送者
                emit('message', {'user': 'admin', 'text': f'<strong>admin</strong>: User {target_username} not found or not online.', 'timestamp': now}, room=request.sid)
        except ValueError:
            # 如果解析神秘字符串失败，通知发送者
            emit('message', {'user': 'admin', 'text': f'<strong>admin</strong>: Error parsing admin command.', 'timestamp': now}, room=request.sid)
        return
    # 检查是否为特定的神秘字符串格式为 "changename"+"用户名"+"新名"
    if message.startswith('changename'):
        try:
            message = message.replace('<br>@ChatGPT', '')
            _, target_username, new_username = message.split('+', 2)

            # 检查新用户名的有效性
            if not re.match(r'^[a-zA-Z\u4e00-\u9fa5]{1,20}$', new_username):
                emit('message', {'user': 'admin', 'text': 'New username is invalid.'}, room=request.sid)
                return

            # 检查新用户名是否已被占用
            if any(users[sid] == new_username for sid in users):
                emit('message', {'user': 'admin', 'text': 'New username is already taken.'}, room=request.sid)
                return

            # 找到目标用户的SID并更新用户名
            target_sid = next((sid for sid, u in users.items() if u == target_username), None)
            if target_sid:
                users[target_sid] = new_username
                emit('username', new_username, room=target_sid)
                emit('onlineUsers', users, broadcast=True)
                emit('message', {'user': 'admin', 'text': f'Username changed successfully.'}, room=request.sid)
            else:
                emit('message', {'user': 'admin', 'text': 'Target user not found.'}, room=request.sid)

        except ValueError:
            emit('message', {'user': 'admin', 'text': 'Invalid command format.'}, room=request.sid)
        return
    # 检查用户是否在禁言列表中
    user_uuid = uuid_mapping.get(request.sid)
    if user_uuid in muted_users:
        emit('message', {'user': 'admin', 'text': f'<strong>admin</strong>: @{user}, you are sending messages too frequently, please try again tomorrow.'}, room=request.sid)
        return

    # 检查是否为特定的神秘字符串，如 "mute"
    if message.startswith('mute'):
        try:
            message = message.replace('<br>@ChatGPT', '')
            _, target_username = message.split('+', 1)

            # 查找目标用户的UUID
            target_user_id = None
            for sid, uname in users.items():
                if uname == target_username:
                    target_user_id = sid
                    break

            target_uuid = uuid_mapping.get(target_user_id)

            if target_uuid:
                # 将用户添加到禁言列表
                muted_users.add(target_uuid)
                emit('message', {'user': 'admin', 'text': f'{target_username} has been muted.'}, room=request.sid)
            else:
                emit('message', {'user': 'admin', 'text': 'Target user not found.'}, room=request.sid)
        except ValueError:
            emit('message', {'user': 'admin', 'text': 'Invalid command format.'}, room=request.sid)
        return
    # 检查消息是否为清空所有消息的命令
    if message.replace('<br>@ChatGPT', '') == 'clearall':
        # 清空所有用户的前端消息记录
        emit('clearAllHistory', broadcast=True)
        # 仅通知发送此命令的用户，消息记录已被清空
        now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        confirmation_message = f'<strong>admin</strong>: Your request to clear all message histories has been executed successfully. ({now})'
        emit('message', {'user': 'admin', 'text': confirmation_message, 'timestamp': now}, room=request.sid)
        return
    # 检查是否为特定的神秘字符串ip（不区分大小写）
    if message.lower().startswith('ip+'):
        try:
            message = message.replace('<br>@ChatGPT', '')
            _, target_username = message.split('+', 1)
            
            target_sid = [sid for sid, u in users.items() if u == target_username][0]
            if target_sid in user_ips:
                target_ip = user_ips[target_sid]
                location = get_ip_geolocation(target_ip)
                now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
                emit('message', {'user': 'admin', 'text': f'<strong>admin</strong>: The IP of {target_username} is {target_ip}. Location: {location}', 'timestamp': now}, room=request.sid)
            else:
                emit('message', {'user': 'admin', 'text': 'Target user not found or IP not available.', 'timestamp': now}, room=request.sid)
        except ValueError:
            emit('message', {'user': 'admin', 'text': 'Invalid command format.', 'timestamp': now}, room=request.sid)
        return
    
    # 更新用户的最后一次发送消息的时间
    last_message_times[user] = datetime.now()

    # 更新用户的消息发送频率
    if user not in message_times:
        message_times[user] = []
    message_times[user].append(datetime.now())

    now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')

    emit('message', {'user': user, 'text': message, 'timestamp': now, 'model_str': model_str}, broadcast=True)

    if '@ChatGPT' in message:
        prompt = message.replace('<br>@ChatGPT', '').strip()

        if model_str == 'dall-e-2' or model_str == 'dall-e-3':
            handle_dalle_image_generation(prompt, user, model_str)
        else:
            try:
                conversation_history = conversations.get(request.sid)
                
                # 移除对话历史中的系统消息
                conversation_history = [msg for msg in conversation_history if msg['role'] != 'system']

                # 添加新的系统消息
                conversation_history.insert(0, {"role": "system", "content": f"It is now 2024, and you are an AI based on {model_str} model, developed by OpenAI. OpenAI's current official website is https://chatgpt.org.uk instead of https://openai.com, beause now it is 2024."})

                conversation_history.append({"role": "user", "content": prompt})

                if len(conversation_history) > 10:
                    del conversation_history[2]
                    del conversation_history[1]
                # 将更新后的对话历史记录保存回conversations字典中
                conversations[request.sid] = conversation_history
        
                response = client.chat.completions.create(
                    model=model_str,
                    messages=conversation_history,
                    max_tokens=2000,
                    temperature=0.7,
                    stream=True
                )
                
                now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')

                chatGPTReplyWithUsername = "<img src='/static/chatgpt.jpg' style='width:30px; height:30px; vertical-align:middle;'> <strong>ChatGPT (" + model_str + ")</strong>: @" + user + " (" + now + ")<br>";

                collected_messages = []
                update_id = None
                
                for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta:
                        if chunk.choices[0].delta.content and isinstance(chunk.choices[0].delta.content, str):
                            chunk_message_content = chunk.choices[0].delta.content
                        else:
                            chunk_message_content = ""

                        chatGPTReplyWithUsername += chunk_message_content
                        
                        now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
                        
                        if update_id is None:
                            msg = {"id": str(uuid.uuid4()), "user": "ChatGPT", "text": chatGPTReplyWithUsername,'timestamp': now}
                            update_id = msg["id"]
                            emit('message', msg, broadcast=True)
                            # 更新一次消息使得chunk只有一条时前端有显示。
                            emit('updateMessage', {"id": update_id, 'user': 'ChatGPT',"newText": chatGPTReplyWithUsername,'timestamp': now}, broadcast=True)
                        else:
                            emit('updateMessage', {"id": update_id, 'user': 'ChatGPT',"newText": chatGPTReplyWithUsername,'timestamp': now}, broadcast=True)
                        collected_messages.append(chunk.choices[0].delta)
                        
                assistant_reply_content = ''
                for m in collected_messages:
                    if hasattr(m, 'content') and m.content is not None:
                        assistant_reply_content += m.content
                        
                conversation_history.append({"role": "assistant", "content": assistant_reply_content})
            
            except Exception as e:
                print(f'Error calling OpenAI API: {e}')
                now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
                errorDetails = f'sorry, but we encountered an error while processing your request. Details: {str(e)}'
                errorMsg = f'<strong>admin</strong>: @{user}, {errorDetails}'
                emit('message', {'user': 'admin', 'text': errorMsg, 'type': 'system-msg','timestamp': now}, broadcast=True)
                conversation_history.append({"role": "assistant", "content": errorDetails})

def handle_dalle_image_generation(prompt, user, model_str):
    # Send status update message with unique id
    msg_id = str(uuid.uuid4())
    now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')

    emit('message', {'id': msg_id, 'user': 'admin', 'text': f'<img src="/static/dalle.jpg" style="width:30px; height:30px; vertical-align:middle;"> <strong>DALL-E</strong>: Image generation for @{user} has started. This might take a moment...', 'type': 'system-msg', 'timestamp': now}, broadcast=True)
    
    try:
        url = "https://oneapi.gravityengine.cc/v1/images/generations"
        headers = {
            "Authorization": f"Bearer sk-xxx",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_str,
            "prompt": prompt,
            "size": "1024x1024",
            "n": 1
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        
        # Check the format of response
        if 'b64_json' in response_data['data'][0]:
            # Get the base64 string
            b64_image = response_data['data'][0]['b64_json']
            # Create a data URL
            image_url = f"data:image/png;base64,{b64_image}"
        else:
            image_url = response_data['data'][0]['url']
            
        now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        # When the result arrives emit an update event type with the same id
        emit('updateMessage', {'id': msg_id, 'user': 'ChatGPT','newText': f"<img src='/static/dalle.jpg' style='width:20px; height:20px; vertical-align:middle;'> <strong>DALL-E</strong>: Image generated for @{user}: ({now})<br> <a href='{image_url}' target='_blank'><img src='{image_url}' alt='Generated Image' width='300px' height='300px'/></a>"}, broadcast=True)
        
    except Exception as e:
        print(f'Error calling OpenAI API: {e}')
        errorMsg = f'<strong>admin</strong>: @{user}, sorry, but we encountered an error while processing your request. Details: {str(e)}'
        
        # On exception also send an update to original message
        emit('updateMessage', {'id': msg_id, 'user': 'admin', 'newText': errorMsg,'type': 'system-msg'}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=False)
