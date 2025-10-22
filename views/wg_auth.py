import asyncio
import re

from authlib.integrations.requests_client import OAuth2Session
from flask import Blueprint, request, redirect, session, render_template

import api
import db
from config import settings
from exception import FlaskCustomError
from openid_wargaming.authentication import Authentication
from openid_wargaming.verification import Verification

loop = asyncio.get_event_loop()


def construct_blueprint(bot, loop):
    app_wg_auth = Blueprint("wg_auth", __name__, url_prefix="")

    @app_wg_auth.route("/wg_link", methods=["GET"])
    def wg_link():
        redirect_uri = settings.FLASK_DOMAIN + request.path
        state = request.args.get("state")
        if state is None:
            raise FlaskCustomError(error_list=["認証エラーが発生しました。",
                                              "お手数ですが再度Discordからお試しください。"], error_code="E20001",
                                   http_code=400)
        discord_std = OAuth2Session(settings.DISCORD_CLIENT_ID, settings.DISCORD_CLIENT_SECRET, state=state,
                                    redirect_uri=redirect_uri)
        token = discord_std.fetch_token("https://discord.com/api/oauth2/token", authorization_response=request.url)
        access_token = token.get("access_token")
        if access_token is None:
            raise FlaskCustomError(error_list=["認証エラーが発生しました。",
                                              "お手数ですが再度Discordからお試しください。"], error_code="E20002",
                                   http_code=400)
        userinfo_request = discord_std.get(f"https://discord.com/api/users/@me")
        userinfo_json = userinfo_request.json()
        discord_id = userinfo_json["id"]
        session["discord_id"] = discord_id
        return_to = f"{settings.FLASK_DOMAIN}/wg_auth"
        auth = Authentication(return_to=return_to)
        url = asyncio.run_coroutine_threadsafe(auth.authenticate(f"https://wargaming.net/id/openid/"),
                                               loop).result()  # noqa
        return redirect(f"https://wargaming.net{url}")

    @app_wg_auth.route("/wg_auth", methods=["GET"])
    def wg_auth():
        """ASIAサーバーユーザーの認証"""
        openid_mode = request.args.get("openid.mode")
        discord_id_str = session.get("discord_id")
        if openid_mode is None:
            raise FlaskCustomError(error_list=["認証エラーが発生しました。",
                                              "お手数ですが再度Discordからお試しください。"], error_code="E10001",
                                   http_code=400)
        if openid_mode == "cancel":
            raise FlaskCustomError(error_list=["認証がキャンセルされました。",
                                                  "お手数ですが再度Discordからお試しください。"], error_code="E10002",
                                   http_code=200)
        if discord_id_str is None:
            raise FlaskCustomError(error_list=["認証エラーが発生しました。",
                                               "制限時間を超過したか、BOTの再起動等によりセッションが切断されました。",
                                               "お手数ですが再度Discordからお試しください。"], error_code="E10003",
                                   http_code=408)
        else:
            discord_id = int(discord_id_str)
            current_url = request.url
            regex = r"https://wargaming.net/id/([0-9]+)-(\w+)/"
            verify = Verification(current_url)
            identities = asyncio.run_coroutine_threadsafe(verify.verify(), loop).result()  # noqa
            if not identities:
                raise FlaskCustomError(error_list=["認証エラーが発生しました。",
                                                   "お手数ですが再度Discordからお試しください。"], error_code="E10001",
                                       http_code=422)
            match = re.search(regex, identities["identity"])
            account_id = match.group(1)
            nickname = match.group(2)
            return comp_auth(discord_id=discord_id, account_id=account_id, nickname=nickname)

    def comp_auth(discord_id: int, account_id: str, nickname: str) -> str:
        """ユーザーの認証"""
        # 認証済みロールの付与
        session.pop("discord_id", None)
        region = asyncio.run_coroutine_threadsafe(api.wows_account_search(account_id, nickname),
                                                  loop).result()  # noqa
        if region == "ERROR":
            raise FlaskCustomError(error_list=["指定されたアカウントにはPC版WoWSのプレイ歴がありません。",
                                                            "お手数ですが指定したアカウントでPC版WoWSを1戦以上プレイしてから再度お試しください。"], error_code="E10002",
                                   http_code=422)
        else:
            from cogs.auth import add_role_authed
            asyncio.run_coroutine_threadsafe(add_role_authed(bot, discord_id), loop)  # noqa
            # DBへの情報の登録
            asyncio.run_coroutine_threadsafe(db.add_user(discord_id, account_id, region), loop)  # noqa
            return render_template('auth_ok.html', region=region, nickname=nickname)

    return app_wg_auth
