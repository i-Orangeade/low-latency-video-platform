FROM python:3.11-slim

WORKDIR /app

# 不写 pyc 可以减少容器镜像中的运行缓存；不缓冲日志便于 docker logs 实时查看。
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 后端镜像只包含 API 逻辑，不包含 ZLMediaKit 和前端静态资源。
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py .

EXPOSE 8000

CMD ["python", "run.py"]
