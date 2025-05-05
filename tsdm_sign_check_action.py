import requests
from datetime import datetime
import random
import time
import re

# 配置日志记录
import json
import logging
import os
  
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
  
# 获取 user_config.json 的相对路径
base_dir = os.path.dirname(os.path.abspath(__file__))
user_config_path = os.path.join(base_dir, 'user_config.json')
# 新增读取 JSON 文件的函数
def read_accounts():
    try:
        with open(user_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f'读取 user_config.json 出错: {e}')
    return []

    # 新增写入 JSON 文件的函数
def write_accounts(accounts):
    try:
        with open(user_config_path, 'w', encoding='utf-8') as f:
              json.dump(accounts, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f'写入 user_config.json 出错: {e}')

def update_lastact(cookie_header_str):
    try:
        if "s_gkr8_682f_lastact" in cookie_header_str:
            current_timestamp = str(int(time.time()))
            start_index = cookie_header_str.find("s_gkr8_682f_lastact=")
            end_index = cookie_header_str.find(";", start_index)
            if end_index == -1:
                end_index = len(cookie_header_str)
            parts = cookie_header_str[start_index:end_index].split("%09", 1)
            if len(parts) > 1:
                new_lastact = "s_gkr8_682f_lastact=" + current_timestamp + "%09" + parts[1]
                cookie_header_str = cookie_header_str[:start_index] + new_lastact + cookie_header_str[end_index:]
        return cookie_header_str
    except Exception as e:
        logging.error(f"更新 lastact 时出错: {e}")
        return cookie_header_str

def check_sign_status(username):
    url = 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign'
    try:
        # 从 JSON 文件查询账号信息
        accounts = read_accounts()
        target_info = next((account for account in accounts if account['username'] == username), None)
        if target_info is None:
            logging.error(f"未找到 {username} 的登录信息，请检查。")
            print(f"未找到 {username} 的登录信息，请检查。")
            return None
        try:
            # 处理单引号问题
            if isinstance(target_info['cookies'], list):
                cookies_list = target_info['cookies']
            else:
                cookies_str = target_info['cookies'].replace("'", "")
                cookies_list = json.loads(cookies_str)  # 使用 JSON 解析将字符串转换为列表
        except json.JSONDecodeError as e:
            print(f"解析 cookies 字符串时出错，原始字符串: {target_info['cookie']}, 错误信息: {e}")  # 打印错误信息
            cookies_list = []  # 默认空列表作为回退方案
        except json.JSONDecodeError:
            print("解析 cookies 字符串时出错，请检查存储的格式。")
            return None
        cookies_dict = {}
        # 将 cookies 列表转换为字典
        for cookie in cookies_list:
            key = cookie.get('name')
            value = cookie.get('value')
            if key and value:
                cookies_dict[key] = value
        # 定义请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Host': 'www.tsdm39.com',
            'Referer': 'https://www.tsdm39.com/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        # 创建会话对象并发送请求
        session = requests.Session()
        response = session.get(url, headers=headers, cookies=cookies_dict)
        response.raise_for_status()
        logging.info(f"请求成功，响应状态码: {response.status_code}")
        # 检查 cookie 是否失效
        invalid_cookie_msg = "您需要先登录才能继续本操作"
        if invalid_cookie_msg in response.text:
            logging.warning(f"{username} 的 cookie 已失效，更新登录信息。")
            target_info['cookie_status'] = False
            write_accounts(accounts)
            return None, None, None
        # 获取当前时间
        now = datetime.now()
        hour = now.hour
        # 检查返回页面是否包含指定文本且当前时间不在 0 点 - 1 点
        target_text = "您今天已经签到过了或者签到时间还未开始"
        if target_text in response.text and not (0 <= hour < 1):
            logging.info("今日已签到")
            # 获取今日日期，只取日期部分
            today_date = now.strftime("%Y-%m-%d")
            try:
                target_info['last_sign_date'] = today_date
                write_accounts(accounts)
            except Exception as e:
                logging.error(f"更新 {username} 的 last_sign_date 时出错: {e}")
            return True, None, None
        # 更灵活的正则表达式来搜索 formhash 的值
        formhash_pattern = r'<input\s+[^>]*name="formhash"\s+[^>]*value="([a-f0-9]+)"'
        match = re.search(formhash_pattern, response.text)
        formhash = None
        if match:
            formhash = match.group(1)
            logging.info(f"找到 formhash: {formhash}")
        else:
            logging.warning("未找到 formhash")
        # 获取新的 cookie
        new_cookies = session.cookies.get_dict()
        # logging.info("新的 Cookie:", new_cookies)
        # 合并新旧 cookies
        merged_cookies = cookies_dict.copy()
        merged_cookies.update(new_cookies)
        # 将合并后的 cookies 转换为符合 Cookie 请求头格式的字符串
        cookie_header_str = "; ".join([f"{key}={value}" for key, value in merged_cookies.items()])
        return False, cookie_header_str, formhash
    except FileNotFoundError as e:
        logging.error(f"未找到 login_info.json 文件: {e}")
        return None, None, None
    except requests.RequestException as e:
        logging.error(f"请求出错: {e}")
        return None, None, None
    except Exception as e:
        logging.error(f"发生未知错误: {e}")
        return None, None, None


def perform_sign(username):
    sign_url = 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1&inajax=1'

    result = check_sign_status(username)
    if result is not None:
        checked, cookie_header_str, formhash = result
    else:
        return
    if checked is True:
        return

    # 定义签到请求头
    sign_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookie_header_str,
        'Host': 'www.tsdm39.com',
        'Origin': 'https://www.tsdm39.com',
        'Referer': 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign',
        'Sec-Fetch-Dest': 'iframe',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'sec-ch-ua': '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    # 打工请求前更新 s_gkr8_682f_lastact
    cookie_header_str = update_lastact(cookie_header_str)
    sign_headers['Cookie'] = cookie_header_str

    # 定义签到的查询字符串参数
    sign_params = {
        'id': 'dsu_paulsign:sign',
        'operation': 'qiandao',
        'infloat': '1',
        'inajax': '1',
    }

    # 可供选择的 qdxq 值列表
    qdxq_options = ['kx', 'ng', 'ym', 'wl', 'nu', 'ch', 'fd', 'yl', 'shuai']
    # 随机选择一个 qdxq 值
    random_qdxq = random.choice(qdxq_options)

    # 定义签到的表单数据
    sign_data = {
        'formhash': formhash,
        'qdxq': random_qdxq,
        'qdmode': '3',
        'todaysay': '',
        'fastreply': '1'
    }

    try:
        # 发送签到请求
        sign_session = requests.Session()
        sign_response = sign_session.post(sign_url, headers=sign_headers, params=sign_params, data=sign_data)
        sign_response.raise_for_status()

        logging.info(f"签到请求成功，响应状态码: {sign_response.status_code}")

        # 再次检查签到状态
        recheck, _, _ = check_sign_status(username)
        if recheck:
            logging.info("签到成功。")
        else:
            logging.warning("签到出错。")

    except requests.RequestException as e:
        logging.error(f"签到请求出错: {e}")
    except Exception as e:
        logging.error(f"发生未知错误: {e}")

if __name__ == '__main__':
    # test_update_db_status()
    # from app import app
    # 示例调用，可替换为实际的用户名
    username = "sscvex" #sscvex
    result = check_sign_status(username)
    if result:
        print("合并后的 Cookie 请求头字符串:", result)