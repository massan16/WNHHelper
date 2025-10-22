from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

COLOR_OK = 0x00ff00
COLOR_WARN = 0xffa500
COLOR_ERROR = 0xff0000


class RoleID(BaseSettings):
    """ 環境変数を読み込む """
    # ロール
    ADMIN: int  # 管理者ロール
    WNH_STAFF: int  # スタッフロール
    CLAN_STAFF: int  # 公認クラン担当スタッフ
    SENIOR_MOD: int  # 上級モデレーターロール
    MOD: int  # モデレーターロール
    CLAN_RECRUITER: int  # 公認クランリクルーターロール
    WAIT_AGREE_RULE: int  # ルール同意前ロール
    WAIT_AUTH: int  # ルール同意後ロール
    AUTHED: int  # 認証済みロール
    MATTARI: int  # まったりロール
    GATSU: int  # がつがつロール
    DIVISION: int  # 分隊ロール

    model_config = SettingsConfigDict(
        env_file=".env.role",
        env_file_encoding="utf-8",
        # extra="ignore",
    )


class ChannelID(BaseSettings):
    """ 環境変数を読み込む """
    RULE: int  # ルールCH
    DIVISION: int  # 分隊募集CH
    MOD_CASE: int  # モデレーション記録CH
    MOD_LOG: int  # モデレーションログCH
    MOD_CONTACT_LOG: int  # 処罰に対する意見等CH
    REPORT_LOG: int  # 報告受付CH
    MESSAGE_LOG: int  # メッセージログCH
    USER_LOG: int  # ユーザーログCH
    EVENT1: int  # イベント_スレッドID
    EVENT2: int  # イベント_スレッドID

    # 問い合わせ
    OPINION_LOG: int  # ご意見・ご要望CH
    GENERAL_INQUIRY_OPEN: int  # その他お問い合わせ
    GENERAL_INQUIRY_CLOSE: int  # その他お問い合わせ
    GENERAL_INQUIRY_LOG: int  # その他お問い合わせ
    GENERAL_INQUIRY_SAVE: int  # その他お問い合わせ
    REPORT_OPEN: int  # 通報
    REPORT_CLOSE: int  # 通報
    REPORT_LOG: int  # 通報
    REPORT_SAVE: int  # 通報
    CLAN_OPEN: int  # 公認クラン
    CLAN_CLOSE: int  # 公認クラン
    CLAN_LOG: int  # 公認クラン
    CLAN_SAVE: int  # 公認クラン
    CLAN_MEET: int  # 公認クラン面談申請

    model_config = SettingsConfigDict(
        env_file=".env.channel",
        env_file_encoding="utf-8",
        # extra="ignore",
    )


class Settings(BaseSettings):
    """ 環境変数を読み込む """
    # ロール
    role_id:RoleID = RoleID()

    # チャンネル
    channel_id: ChannelID = ChannelID()

    GUILD_ID: int  # サーバーID
    # シークレット
    # DB接続情報
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    FLASK_SERVICE_PORT: int  # Flask Port
    FLASK_DOMAIN: str  # Flask Domain
    FLASK_SECRET_KEY: str  # Flask Secret Key
    WARGAMING_APPLICATION_ID: str  # Wargaming ApplicationID
    DISCORD_TOKEN: str  # Discord Token
    DISCORD_CLIENT_ID: str  # Discord Client ID
    DISCORD_CLIENT_SECRET: str  # Discord Client Secret

    BLOCKED_IP_PREFIXES: str

    ENV: str  # 環境

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # extra="ignore",
    )


# インスタンス化して環境変数を読み込む

settings = Settings()
BLOCKED_IP_PREFIXES_LIST = settings.BLOCKED_IP_PREFIXES.replace("\n", "").replace(" ", "").split(",")
