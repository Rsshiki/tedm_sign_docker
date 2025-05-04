import requests
import re
from datetime import datetime, timedelta
import time
import random
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

def check_work_status(username):
    url = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

    try:
        # 从 JSON 文件查询账号信息
        accounts = read_accounts()
        target_info = next((account for account in accounts if account['username'] == username), None)
        if target_info is None:
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

        print("请求成功，响应状态码: %d", response.status_code)

        # 检查 cookie 是否失效
        invalid_cookie_msg = "请先登录再进行点击任务"
        if invalid_cookie_msg in response.text:
            print(f"{username} 的 cookie 已失效，更新登录信息。")
            target_info['cookie_status'] = '失效'
            write_accounts(accounts)
            return None

        # 提取等待时间
        pattern = r"您需要等待(\d+)小时(\d+)分钟(\d+)秒后即可进行。"
        match = re.search(pattern, response.text)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            wait_time = timedelta(hours=hours, minutes=minutes, seconds=seconds)

            # 先减去 6 小时，再加上等待时间得到上次打工时间
            now = datetime.now()
            six_hours_ago = now - timedelta(hours=6)
            last_work_time = six_hours_ago + wait_time

            # 转换为字符串格式
            last_work_time_str = last_work_time.strftime("%Y-%m-%d %H:%M:%S")

            # 更新 JSON 文件中对应用户名的 last_work_time
            target_info['last_work_time'] = last_work_time_str
            write_accounts(accounts)

            print(f"{username} 已打过工，正在冷却状态。")
            return None

        # 获取新的 cookie
        new_cookies = session.cookies.get_dict()
        # print("新的 Cookie:", new_cookies)
        # 合并新旧 cookies
        merged_cookies = cookies_dict.copy()
        merged_cookies.update(new_cookies)

        # 将合并后的 cookies 转换为符合 Cookie 请求头格式的字符串
        cookie_header_str = "; ".join([f"{key}={value}" for key, value in merged_cookies.items()])

        # print(f"{username} 的 Cookie 已更新。")
        return cookie_header_str

    except FileNotFoundError:
        print("未找到 login_info.json 文件。")
        return None
    except requests.RequestException as e:
        print(f"请求出错: {e}")
        return None

def perform_work(username):
    # 调用补全cookie函数获取合并后的Cookie字符串
    cookie_header_str = check_work_status(username)
    if cookie_header_str is None:
        return
    if not cookie_header_str:
        print("未获取到有效的Cookie字符串，无法继续操作。")
        return

    # 定义点广告的 URL
    ad_url = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

    # 定义点广告的请求头
    ad_headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookie_header_str,
        'Host': 'www.tsdm39.com',
        'Origin': 'https://www.tsdm39.com',
        'Referer': 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': 'Windows'
    }

    # 定义点广告的查询字符串参数
    ad_params = {
        'id': 'np_cliworkdz:work'
    }

    # 定义点广告的表单数据
    ad_data = {
        'act': 'clickad'
    }

    while True:
        # 每次请求前更新 s_gkr8_682f_lastact
        cookie_header_str = update_lastact(cookie_header_str)
        ad_headers['Cookie'] = cookie_header_str

        try:
            # 发送点广告请求
            ad_session = requests.Session()
            ad_response = ad_session.post(ad_url, headers=ad_headers, params=ad_params, data=ad_data)
            ad_response.raise_for_status()

            print("点广告请求成功，响应状态码: %d", ad_response.status_code)
            # 打印响应内容
            ad_response_text = ad_response.text.strip()
            print("点广告响应内容:", ad_response_text)

            if ad_response_text == "6":
                print("点广告获得返回值 6，开始打工请求。")
                break
            elif ad_response_text in ["1", "2", "3", "4", "5"]:
                # 生成 1 - 2 秒之间的随机间隔时间
                sleep_time = random.uniform(1, 2)
                print(f"点广告返回值为 {ad_response_text}，等待 {sleep_time:.3f} 秒后继续请求。")
                time.sleep(sleep_time)
            else:
                print(f"点广告收到意外返回值 {ad_response_text}，停止操作。")
                return

        except requests.RequestException as e:
            print(f"点广告请求出错: {e}")
            return

    # 定义打工的 URL
    work_url = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

    # 定义打工的请求头
    work_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookie_header_str,
        'Host': 'www.tsdm39.com',
        'Origin': 'https://www.tsdm39.com',
        'Referer': 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work',
        'Sec-Fetch-Dest': 'document',
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
    work_headers['Cookie'] = cookie_header_str

    # 定义打工的查询字符串参数
    work_params = {
        'id': 'np_cliworkdz:work'
    }

    # 定义打工的表单数据
    work_data = {
        'act': 'getcre'
    }

    try:
        # 发送打工请求
        work_session = requests.Session()
        work_response = work_session.post(work_url, headers=work_headers, params=work_params, data=work_data)
        work_response.raise_for_status()

        print("打工请求成功，响应状态码: %d", work_response.status_code)

        target_content = '恭喜，您已经成功领取了奖励天使币'
        if target_content in work_response.text:
            # 再次检查签到状态
            recheck = check_work_status(username)
            if recheck is None:
                print("打工完成。")
            else:
                print("打工出错。")

    except requests.RequestException as e:
        print(f"打工请求出错: {e}")
        return False

if __name__ == "__main__":
    # 示例调用，可替换为实际的用户名
    username = "sscvex" #sscvex
    result = check_work_status(username)
    if result:
        print("合并后的 Cookie 请求头字符串:", result)