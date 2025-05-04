from flask import Flask, render_template, request, send_file, jsonify, redirect, session
import io
from tsdm_login import update_verification_code, submit
import time
import json
from tsdm_work_check_action import perform_work
from tsdm_sign_check_action import perform_sign
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/')
def index():
    if 'username' in session:
        return redirect('/home')
    return render_template('index.html')

@app.route('/get_verification_code')
def get_verification_code():
    img_data = update_verification_code()
    if img_data:
        img_io = io.BytesIO(img_data)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')
    return jsonify({'error': '获取验证码失败'}), 500

@app.route('/submit', methods=['POST'])
def login_submit():
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        return jsonify({'error': '请输入用户名、密码和验证码'}), 400
    if username == 'admin' and password == 'admin':
        session['username'] = username
        return jsonify({'message': '登录成功', 'redirect': '/home'})
    return jsonify({'error': '用户名或密码错误'}), 401

@app.route('/home')
def home():
    if 'username' in session:
        return render_template('home.html')
    return redirect('/')

@app.route('/account_manger.html')
def account_manager():
    if 'username' in session:
        try:
            with open('user_config.json', 'r', encoding='utf-8') as f:
                accounts = json.load(f)
        except FileNotFoundError:
            accounts = []
        except json.JSONDecodeError:
            accounts = []
        return render_template('account_manger.html', accounts=accounts)
    return redirect('/')

@app.route('/seting.html')
def seting():
    if 'username' in session:
        return render_template('seting.html')
    return redirect('/')

@app.route('/add_account.html')
def add_account():
    if 'username' in session:
        return render_template('add_account.html')
    return redirect('/')

@app.route('/add_user', methods=['POST'])
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    verification_code = request.form.get('verification_code')
    if not username or not password or not verification_code:
        return jsonify({'error': '请输入用户名、密码和验证码'}), 400
    success, result = submit(username, password, verification_code)
    if success:
        from config import save_user_info
        save_user_info(username, password, result)
        return jsonify({'message': '登录成功', 'cookies': result})
    return jsonify({'error': result}), 401
    print(result)

@app.route('/sign_in', methods=['POST'])
def sign_in():
    data = request.get_json()
    username = data.get('username')
    # 这里添加签到逻辑
    return jsonify({'message': f'{username} 签到成功'})

@app.route('/go_to_work', methods=['POST'])
def go_to_work():
    data = request.get_json()
    username = data.get('username')
    # 这里添加打工逻辑
    return jsonify({'message': f'{username} 打工成功'})

@app.route('/delete_account', methods=['POST'])
def delete_account():
    data = request.get_json()
    username = data.get('username')
    try:
        with open('user_config.json', 'r', encoding='utf-8') as f:
            accounts = json.load(f)
        accounts = [acc for acc in accounts if acc['username'] != username]
        with open('user_config.json', 'w', encoding='utf-8') as f:
            json.dump(accounts, f, indent=4)
        return jsonify({'message': f'{username} 删除成功', 'success': True})
    except Exception as e:
        return jsonify({'message': f'删除失败: {str(e)}', 'success': False})

@app.route('/add_task', methods=['POST'])
def add_task():
    data = request.get_json()
    task_type = data.get('task_type')
    username = data.get('username')
    if task_type and username:
        global TASK_LIST
        TASK_LIST.append((task_type, username))
        return jsonify({'message': f'{username} 的 {task_type} 任务已添加到列表', 'success': True})
    return jsonify({'error': '缺少任务类型或用户名', 'success': False})


# 使用全局变量存储任务列表
TASK_LIST = []


def process_task(task):
    task_type, username = task
    if task_type in ('work', '打工'):
        perform_work(username)
    elif task_type in ('sign', '签到'):
        perform_sign(username)
    else:
        print(f'未知任务类型: {task_type}')


def monitor_tasks():
    global TASK_LIST
    while True:
        if TASK_LIST:
            task = TASK_LIST.pop(0)
            print(f'开始处理任务: {task}')
            process_task(task)
            print(f'任务 {task} 处理完成，已从列表移除。')
        time.sleep(5)  # 每5秒检查一次任务列表

if __name__ == '__main__':
    monitor_thread = threading.Thread(target=monitor_tasks)
    monitor_thread.daemon = True
    monitor_thread.start()
    app.run(debug=True)