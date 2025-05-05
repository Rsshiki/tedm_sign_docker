import requests
from flask import session
from bs4 import BeautifulSoup
import time
def update_verification_code():
    login_url = 'https://www.tsdm39.com/member.php?mod=logging&action=login'
    base_url = 'https://www.tsdm39.com/'
    headers1 = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    }
    try:
        session = requests.Session()
        response = session.get(login_url, headers=headers1)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        verify_img = soup.find('img', class_='tsdm_verify')
        if verify_img:
            verify_img_url = verify_img.get('src')
            if verify_img_url:
                full_verify_img_url = base_url + verify_img_url if not verify_img_url.startswith('http') else verify_img_url
                img_response = session.get(full_verify_img_url, headers=headers1)
                img_response.raise_for_status()
                img_data = img_response.content
                return img_data
    except requests.RequestException as e:
        print(f"请求出错: {e}")

def submit(username, password, verification_code):
    login_url = 'https://www.tsdm39.com/member.php?mod=logging&action=login'
    base_url = 'https://www.tsdm39.com/'
    headers1 = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    }
    session = requests.Session()
    try:
        response = session.get(login_url, headers=headers1)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        formhash_input = soup.find('input', {'name': 'formhash'})
        formhash = formhash_input.get('value') if formhash_input else ''
        main_message_div = soup.find('div', id=lambda x: x and x.startswith('main_messaqge_'))
        loginhash = main_message_div.get('id').split('main_messaqge_')[-1] if main_message_div else ''
        a1cookies = session.cookies.get_dict()
        if "s_gkr8_682f_lastact" in a1cookies:
            current_timestamp = str(int(time.time()))
            parts = a1cookies["s_gkr8_682f_lastact"].split("%09", 1)
            if len(parts) > 1:
                new_lastact = current_timestamp + "%09" + parts[1]
                a1cookies["s_gkr8_682f_lastact"] = new_lastact
        session.cookies.update(a1cookies)
        new_cookie = "; ".join([f"{key}={value}" for key, value in a1cookies.items()])
        headers2 = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': new_cookie,
            'Host': 'www.tsdm39.com',
            'Origin': 'https://www.tsdm39.com',
            'Referer': 'https://www.tsdm39.com/member.php?mod=logging&action=login',
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
        params = {
            'mod': 'logging',
            'action': 'login',
            'loginsubmit': 'yes',
            'handlekey': 'ls',
            'loginhash': loginhash
        }
        data = {
            'formhash': formhash,
            'referer': 'https://www.tsdm39.com/./',
            'loginfield': 'username',
            'username': username,
            'password': password,
            'tsdm_verify': verification_code,
            'questionid': 0,
            'answer': '',
            'loginsubmit': 'true'
        }
        cur_login_url = f'{base_url}/member.php?mod=logging&action=login&loginsubmit=yes&loginhash={loginhash}'
        login_response = session.post(cur_login_url, headers=headers2, params=params, data=data)
        login_response.raise_for_status()
        print("登录请求已发送，响应状态码:", login_response.status_code)

        if "欢迎您回来" in login_response.text:
            print(f"{username}登录成功！")
            # with open('page_after_login.html', 'w', encoding='utf-8') as html_file:
            #     html_file.write(login_response.text)
            # logger.info("登录后的页面 HTML 已保存到 page_after_login.html")

            cookies_after_login = session.cookies.get_dict()
            cookies_list = []
            for key, value in cookies_after_login.items():
                cookies_list.append({
                    "name": key,
                    "value": value
                })

            return True, cookies_list
        else:
            return False, "登录失败，请检查用户名、密码和验证码。"
    except requests.RequestException as e:
        return False, f"请求出错: {e}"