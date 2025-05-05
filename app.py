from flask import Flask, render_template, request, send_file, jsonify, redirect, session
import io
from tsdm_login import update_verification_code, submit
import time
import json
from tsdm_work_check_action import perform_work
from tsdm_sign_check_action import perform_sign
import threading
import logging
from datetime import datetime as dt, timedelta as td

# 新增：初始化自动打工状态
is_automation_running = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        # 异步执行添加任务逻辑
        threading.Thread(target=add_task_to_queue, args=(task_type, username)).start()
        return jsonify({'success': True})
    return jsonify({'error': '缺少任务类型或用户名', 'success': False})

def add_task_to_queue(task_type, username):
    task = (task_type, username)
    global TASK_LIST
    if task not in TASK_LIST:
        logging.info(f"添加 {username} 的 {task_type} 任务")
        TASK_LIST.append(task)
        logging.info(f"更新任务队列: {TASK_LIST}")
        if not automation_manager.is_task_running:
            automation_manager.execute_task_if_available()

# 使用全局变量存储任务列表
TASK_LIST = []

class AutomationManager:
    def __init__(self):
        self.is_automation_running = False
        self.current_time = None
        self.is_task_running = False
        self.current_task_index = -1

    def update_all_time_dependent_info(self):
        # 每秒获取一次当前时间
        current_time = dt.now()
        # print(f"当前时间: {current_time}")
        self.current_time = current_time
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open('user_config.json', 'r', encoding='utf-8') as f:
                accounts = json.load(f)
        except FileNotFoundError:
            accounts = []
        except json.JSONDecodeError:
            accounts = []

        global TASK_LIST
        task_added = False  # 新增标志变量，用于记录是否添加了新任务
        # 自动化功能逻辑
        if self.is_automation_running:
            # print("自动任务运行中...")
            for account_info in accounts:
                username = account_info.get("username")
                if not username:
                    continue

                is_valid = account_info.get("cookie_status")
                current_date = self.current_time.strftime("%Y-%m-%d")
                last_sign_date = account_info.get("last_sign_date", "")
                sign_status = last_sign_date == current_date
                current_hour = self.current_time.hour
                cool_down_text = self.calculate_work_cool_down(account_info)

                # 输出日志，检查判断条件
                # logging.info(f"账号: {username}, 签到状态: {sign_status}, 当前小时: {current_hour}, 冷却时间: {cool_down_text}")

                # 自动签到逻辑
                if is_valid and not sign_status and not (0 <= current_hour < 1):
                    sign_task = ('sign', username)
                    if sign_task not in TASK_LIST:
                        TASK_LIST.append(sign_task)
                        logging.info(f"添加 {username} 的签到任务")
                        task_added = True  # 标记有新任务添加
                # 自动打工逻辑
                if is_valid and cool_down_text == "00:00:00":
                    work_task = ('work', username)
                    if work_task not in TASK_LIST:
                        TASK_LIST.append(work_task)
                        logging.info(f"添加 {username} 的打工任务")
                        task_added = True  # 标记有新任务添加

        # 只有当有新任务添加时，才调用 execute_task_if_available 方法
        if task_added:
            # logging.info(f"更新任务队列: {TASK_LIST}")
            self.execute_task_if_available()

    def execute_task_if_available(self):
        global TASK_LIST
        if TASK_LIST and not self.is_task_running:
            # 不立即从队列中移除任务，只记录当前任务索引
            self.current_task_index += 1
            if self.current_task_index < len(TASK_LIST):
                task_type, username = TASK_LIST[self.current_task_index]
                logging.info(f"即将执行任务 {task_type} - {username}，当前任务队列: {TASK_LIST}")
                self.is_task_running = True
                if task_type == 'sign':
                    logging.info(f"自动为用户 {username} 启动签到")
                    self.start_sign_for_user(username, callback=self.task_complete)
                elif task_type == 'work':
                    logging.info(f"自动为用户 {username} 启动打工")
                    self.start_work_for_user(username, callback=self.task_complete)
            else:
                # 若索引超出队列长度，重置索引
                self.current_task_index = -1

    def task_complete(self):
        self.is_task_running = False  # 任务完成，解锁
        global TASK_LIST
        if self.current_task_index >= 0 and self.current_task_index < len(TASK_LIST):
            # 任务完成后，从队列中移除当前任务
            completed_task = TASK_LIST.pop(self.current_task_index)
            logging.info(f"任务 {completed_task} 已完成，从队列中移除，当前任务队列: {TASK_LIST}")
            # 由于移除了任务，需要调整当前索引
            self.current_task_index -= 1

        unique_tasks = []
        seen = set()
        for task in TASK_LIST:
            if task not in seen:
                unique_tasks.append(task)
                seen.add(task)
        TASK_LIST = unique_tasks

        # 任务完成后，尝试执行下一个任务
        self.execute_task_if_available()

    def calculate_work_cool_down(self, account_info): # 计算打工冷却时间
        last_work_time_str = account_info.get("last_work_time", "")
        if last_work_time_str:
            try:
                last_work_time = dt.strptime(last_work_time_str, "%Y-%m-%d %H:%M:%S")
                cool_down_end_time = last_work_time + td(hours=6)
                remaining_time = cool_down_end_time - self.current_time
                if remaining_time.total_seconds() > 0:
                    total_seconds = int(remaining_time.total_seconds()) + (1 if remaining_time.microseconds > 0 else 0)
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except ValueError:
                logging.error(f"解析 last_work_time {last_work_time_str} 时出错，格式可能不正确")
        return "00:00:00"

    def start_sign_for_user(self, username, callback=None):
        perform_sign(username)
        if callback:
            callback()

    def start_work_for_user(self, username, callback=None):
        perform_work(username)
        if callback:
            callback()

# 新增：获取自动打工状态的路由
@app.route('/get_automation_status', methods=['GET'])
def get_automation_status():
    global is_automation_running
    return jsonify({'status': is_automation_running})

# 新增：切换自动打工状态的路由
@app.route('/toggle_automation', methods=['POST'])
def toggle_automation():
    global is_automation_running
    data = request.get_json()
    new_status = data.get('status')
    if new_status is not None:
        is_automation_running = new_status
        automation_manager.is_automation_running = new_status
        logging.info(f"自动打工状态已更新: {is_automation_running}")
        return jsonify({'message': '自动打工状态已更新', 'status': is_automation_running})
    return jsonify({'error': '无效的状态参数'}), 400

# 初始化自动化管理器
automation_manager = AutomationManager()

# 新增定时线程，每秒调用一次 update_all_time_dependent_info 函数
def time_dependent_info_updater():
    while True:
        automation_manager.update_all_time_dependent_info()
        time.sleep(1)

if __name__ == '__main__':
    # 启动定时线程
    time_dependent_info_thread = threading.Thread(target=time_dependent_info_updater)
    time_dependent_info_thread.daemon = True
    time_dependent_info_thread.start()