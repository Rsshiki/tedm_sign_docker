import json
import os


def save_user_info(username, password, cookies):
    # 使用相对路径，适配Docker容器环境
    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_config_path = os.path.join(base_dir, 'user_config.json')
    try:
        with open(user_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        users = config.get('accounts', [])
        status = config.get('status', False)
    except (FileNotFoundError, json.JSONDecodeError):
        users = []
        status = False
    
    # 检查是否存在相同用户名，若存在则覆盖
    for user in users:
        if user['username'] == username:
            user['password'] = password
            user['cookies'] = cookies
            break
    else:
        # 若不存在则新增
        new_user = {
            'username': username,
            'password': password,
            'cookies': cookies,
            'cookie_status': True,
            'last_sign_date': None,
            'last_work_time': None
        }
        users.append(new_user)
    
    with open(user_config_path, 'w', encoding='utf-8') as f:
        json.dump({
            'accounts': users,
            'status': status
        }, f, ensure_ascii=False, indent=4)