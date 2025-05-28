from celery import Celery
import os

# 環境変数からRedisのURLを取得する（推奨）か、デフォルト値を設定
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Celeryアプリケーションのインスタンスを作成
# `main`引数はCeleryアプリケーションの名前空間を指定。通常はアプリケーションのメインモジュール名。
# ここでは 'web_api.celery_app' など、このファイル自身を参照するように設定。
# `broker`と`backend`にRedisのURLを指定。
celery_app = Celery(
    'web_api', # Usually the name of the main module where celery is defined or the project
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'web_api.tasks' # We will create tasks in web_api/tasks.py
    ]
)

# Optional Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],  # Ignore other content
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # task_track_started=True, # To report 'started' state (requires result backend)
    # worker_prefetch_multiplier=1, # May be useful for long-running tasks
)

# Example: If you want to load config from a separate module (e.g., celeryconfig.py)
# app.config_from_object('web_api.celeryconfig')

if __name__ == '__main__':
    # This allows running the worker directly using: python -m web_api.celery_app worker ...
    # However, the standard way is `celery -A web_api.celery_app worker ...`
    celery_app.start()
