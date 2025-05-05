# 使用 Python 3.13.2 基础镜像
FROM python:3.13.2-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口，根据实际项目调整
EXPOSE 6865

# 启动命令，使用 Gunicorn 作为 WSGI 服务器
CMD ["gunicorn", "--bind", "0.0.0.0:6865", "app:app"]