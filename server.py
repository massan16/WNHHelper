import asyncio
import logging
import os
import signal
import sys
from collections.abc import Awaitable, Callable, Coroutine
from datetime import timedelta

import dotenv
from authlib.integrations.flask_client import OAuth
from cachelib.file import FileSystemCache
from flask import Flask, render_template, request
from hypercorn.asyncio import serve
from hypercorn.config import Config as HyperConfig

from config import settings, BLOCKED_IP_PREFIXES_LIST
from exception import FlaskCustomError
from flask_session import Session
from logs import server_logger as logger
from views.wg_auth import construct_blueprint as app_wg_auth

env_path = os.path.join(os.path.dirname(__file__), '../.env')
hypercorn_access_logger = logger.getChild("access")
hypercorn_access_logger.setLevel(logging.INFO)
hypercorn_error_logger = logger.getChild("error")
hypercorn_error_logger.setLevel(logging.ERROR)
shutdown_event = asyncio.Event()


class App(Flask):
    def run_task(
            self,
            host: str = "127.0.0.1",
            port: int = 5000,
            debug: bool | None = None,
            ca_certs: str | None = None,
            certfile: str | None = None,
            keyfile: str | None = None,
            shutdown_trigger: Callable[..., Awaitable[None]] | None = None,
    ) -> Coroutine[None, None, None]:
        config = HyperConfig()
        config.access_log_format = "%({X-Forwarded-For}i)s %(r)s %(s)s %(b)s %(D)s"
        config.accesslog = hypercorn_access_logger  # I modified this
        config.bind = [f"{host}:{port}"]
        config.ca_certs = ca_certs
        config.certfile = certfile
        if debug is not None:
            self.debug = debug
        config.errorlog = hypercorn_error_logger  # I modified this
        config.keyfile = keyfile
        config.use_reloader = True
        return serve(self, config, shutdown_trigger=shutdown_event.wait)


app = None
bot_obj = None
public_url = None
server_task = None
_app = App(__name__, static_url_path="/")
oauth = OAuth()
sess = Session()


def create_app(bot, loop) -> Flask:
    global public_url

    _app.config.from_mapping(
        BASE_URL=f"{settings.FLASK_DOMAIN}/",
        PREFERRED_URL_SCHEME="https",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=5),
        SECRET_KEY=settings.FLASK_SECRET_KEY,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_PERMANENT=False,
        SESSION_TYPE="cachelib",
        SESSION_CACHELIB=FileSystemCache(threshold=250, cache_dir="flask_session"),
    )
    public_url = f"{settings.FLASK_DOMAIN}/"
    _app.register_blueprint(app_wg_auth(bot, loop))
    oauth.init_app(_app)
    sess.init_app(_app)
    return _app


def shutdown_server():
    print("サーバーをシャットダウンしています")
    shutdown_event.set()
    return


def signal_handler(_, __):
    shutdown_server()
    return


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
if sys.platform == "win32":
    signal.signal(signal.SIGBREAK, signal_handler)
else:
    signal.signal(signal.SIGTRAP, signal_handler)


def blocked(remote_addr):
    for prefix in BLOCKED_IP_PREFIXES_LIST:
        if remote_addr.startswith(prefix):
            return True
    else:
        return False


def under_trying_hack(path):
    if path.endswith("php"):
        return True
    else:
        return False


@_app.before_request
def before_request():
    """禁止ネットワークからのアクセスか判定"""
    if request.headers.getlist("X-Forwarded-For"):
        remote_addr = request.headers.getlist("X-Forwarded-For")[0]
        if blocked(remote_addr):
            raise FlaskCustomError(error_list=["運営チームまでお問い合わせください"], error_code="E40301", http_code=403)
    elif settings.ENV == "prod":
        remote_addr = request.remote_addr
        sparked_ip = "23.230.3.203"
        if blocked(remote_addr):
            raise FlaskCustomError(error_list=["運営チームまでお問い合わせください"], error_code="E40302", http_code=403)
        elif not remote_addr == sparked_ip:
            BLOCKED_IP_PREFIXES_LIST.append(".".join(remote_addr.split(".")[0:3]) + ".")
            dotenv.set_key(".env", "BLOCKED_IP_PREFIXES", ", ".join(BLOCKED_IP_PREFIXES_LIST))
            raise FlaskCustomError(error_list=["運営チームまでお問い合わせください"], error_code="E40304", http_code=403)
    else:
        remote_addr = request.remote_addr
        if blocked(remote_addr):
            raise FlaskCustomError(error_list=["運営チームまでお問い合わせください"], error_code="E40303", http_code=403)
    if under_trying_hack(request.path):
        BLOCKED_IP_PREFIXES_LIST.append(".".join(remote_addr.split(".")[0:3]) + ".")
        dotenv.set_key(".env", "BLOCKED_IP_PREFIXES", ", ".join(BLOCKED_IP_PREFIXES_LIST))
        raise FlaskCustomError(error_list=["運営チームまでお問い合わせください"], error_code="E40305", http_code=403)


@_app.route("/", methods=["GET"])
def default():
    raise FlaskCustomError(error_list=["運営チームまでお問い合わせください"],
                           error_code="E403", http_code=403)


@_app.errorhandler(403)
def error_403(error):
    """500エラーが発生した場合の処理"""
    return render_template('custom_error.html', error_list=[], error_code="E403", http_code=403)


@_app.errorhandler(500)
def error_500(error):
    """500エラーが発生した場合の処理"""
    return render_template('custom_error.html',
                           error_list=["エラーが発生しました", "お手数ですが再度お試しください",
                                       "改善しない場合は運営チームまでお問い合わせください"],
                           error_code="E500", http_code=500)


@_app.errorhandler(FlaskCustomError)
def handle_custom_error(e):
    return render_template('custom_error.html', http_code=e.http_code, http_msg=e.http_msg, error_list=e.error_list,
                           error_code=e.error_code), e.http_code


oauth.register(
    name="discord_std",
    client_id=settings.DISCORD_CLIENT_ID,
    client_secret=settings.DISCORD_CLIENT_SECRET,
    authorize_url="https://discord.com/api/oauth2/authorize",
    access_token_url="https://discord.com/api/oauth2/token",
    client_kwargs={
        "scope": "identify",
        "prompt": "consent"
    },
)


def wg_auth_link():
    """ASIAサーバー用認証リンクの生成"""
    discord_std = oauth.discord_std
    redirect_uri = settings.FLASK_DOMAIN + f"/wg_link"
    url = discord_std.create_authorization_url(redirect_uri)
    return url["url"]


def run_server(bot, loop):
    """サーバーの起動"""
    global app
    global bot_obj
    global server_task
    bot_obj = bot

    app = create_app(bot, loop)
    ctx = app.app_context()
    ctx.push()
    print("サーバー起動中")
    server_task = loop.create_task(
        app.run_task(host="0.0.0.0", port=settings.FLASK_SERVICE_PORT, debug=False,
                     shutdown_trigger=shutdown_event.wait))  # noqa
    return
