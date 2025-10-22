import time

import discord
from discord import ui
from discord.ext import commands

import db
from bot import DISALLOW_MENTION
from config import COLOR_OK, COLOR_ERROR, settings
from exception import discord_error
from logs import discord_logger as logger

logger = logger.getChild("division")


class Division(commands.Cog):
    """コマンド実装用のクラス"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def create_message(self, interaction: discord.Interaction):
        """分隊募集案内メッセージを送信"""
        # ビューを含むメッセージを送信
        channel = interaction.channel
        await channel.send(view=DivisionView(), allowed_mentions=DISALLOW_MENTION)
        # コマンドへのレスポンス
        response_embed = discord.Embed(description="ℹ️ 送信が完了しました", color=COLOR_OK)
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  # noqa
        # ログの保存
        logger.info(f"{interaction.user.display_name}（UID：{interaction.user.id}）"
                    f"がコマンド「{interaction.command.name}」を使用しました。")

    async def cog_app_command_error(self, interaction, error):
        """コマンド実行時のエラー処理"""
        await discord_error(interaction.command.name, interaction, error, logger)


"""ボタンの実装"""


class DivisionView(ui.LayoutView):
    """分隊募集方法案内メッセージ"""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    text1 = ui.TextDisplay("## 分隊募集について\n"
                           "当サーバーでの分隊募集の告知は次の手順でご利用いただけます\n"
                           "※分隊をする際に告知を行う義務はありません。<#982862998412595220>で集まった方と行っていただくことも可能です。")
    text2 = ui.TextDisplay("### 募集方法\n"
                           "1. 下のボタンを押して分隊募集フォームを開きます\n"
                           "（このフォームを募集した分隊はこのサーバーのVCを使用してください）\n"
                           "2. <#979965008836456449>に募集メッセージとスレッドが作成されますので、注視して下さい。\n"
                           "3. 募集を終了する場合、再開などの変更がある場合はスレッドにその旨を書き込んで下さい。")
    text3 = ui.TextDisplay("### 参加方法\n"
                           "<#979965008836456449>から参加したい分隊を探し、見つけた場合はスレッドに書き込みます（チャンネルには書き込めません）\n"
                           "※VCに直接入っていただいても構いません")
    text4 = ui.TextDisplay("### 分隊募集通知について\n"
                           "分隊募集の通知が欲しい人は下のボタンを押すと専用ロールが付与されます\n"
                           "不要になった場合は再度押して下さい。")
    container = ui.Container(text1, text2, text3, text4)

    action_row = ui.ActionRow()

    @action_row.button(label="分隊通知ロールの取得/解除", emoji="🤝", style=discord.ButtonStyle.blurple,  # noqa
                       custom_id="division")  # noqa
    async def division_role_button(self, interaction: discord.Interaction, button: ui.Button):
        await division_role_button_callback(interaction, button)

    @action_row.button(label="分隊を募集する", style=discord.ButtonStyle.blurple,  # noqa
                       custom_id="division_role")
    async def division_form_button(self, interaction: discord.Interaction, button: ui.Button):
        await division_form_button_callback(interaction, button)


async def division_role_button_callback(interaction: discord.Interaction, button: ui.Button):
    """分隊ロール取得/削除ボタンの処理

    ボタン系はボタンのcallbackに直接書かず、別関数にすることによって処理内容変更後にボタンを再生成せずとも反映できる。
    """
    # ロールを取得
    div_role = interaction.guild.get_role(settings.role_id.DIVISION)
    role = interaction.user.get_role(settings.role_id.DIVISION)
    # ロールがある場合は削除
    if role is not None:
        response_embed = discord.Embed(description=f"ℹ️ <@&{settings.role_id.DIVISION}>を削除しました。", color=COLOR_OK)
        await interaction.user.remove_roles(div_role, reason="分隊ロールボタンによる")
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  # noqa
    # ロールがない場合は追加
    else:
        response_embed = discord.Embed(description=f"ℹ️ <@&{settings.role_id.DIVISION}>を取得しました。", color=COLOR_OK)
        await interaction.user.add_roles(div_role, reason="分隊ロールボタンによる")
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  # noqa


async def division_form_button_callback(interaction: discord.Interaction, button: ui.Button):
    """分隊募集ボタンの処理

    ボタン系はボタンのcallbackに直接書かず、別関数にすることによって処理内容変更後にボタンを再生成せずとも反映できる。
    """
    if interaction.user.is_timed_out():
        error_embed = discord.Embed(description="⚠️ タイムアウト中は利用できません", color=COLOR_ERROR)
        await interaction.response.send_message(embed=error_embed, ephemeral=True)  # noqa
    else:
        # フォームの呼び出し
        await interaction.response.send_modal(DivisionForm())  # noqa


class DivisionForm(ui.Modal, title="分隊募集フォーム"):
    """フォームの実装"""

    def __init__(self):
        """ギルド、ロール、チャンネルの事前定義"""
        super().__init__()

    # フォームの入力項目の定義（最大5個）

    dtime = ui.Label(
        text="1.日時",
        component=ui.TextInput(
            placeholder="例：今日19:00～21:00",
            max_length=30,
        ),
    )

    tier = ui.Label(
        text="2.Tier（オペレーションの場合は名称）",
        component=ui.TextInput(
            placeholder="例：8～10",
            max_length=30,
        ),
    )

    member_count = ui.Label(
        text="3.募集人数",
        component=ui.TextInput(
            placeholder="例：2人",
            max_length=30,
        ),
    )

    newbie = discord.ui.Label(
        text="4.初心者ですか？",
        description="初心者の定義：ランダム戦の戦闘数が3000戦以下の方",
        component=discord.ui.Select(
            options=[
                discord.SelectOption(label="はい"),
                discord.SelectOption(label="いいえ"),
                discord.SelectOption(label="無回答"),
            ],
        ),
    )

    other = ui.Label(
        text="5.その他注記事項（無回答でもOK）",
        component=ui.TextInput(
            style=discord.TextStyle.long,  # noqa
            required=False,
            max_length=300,
        ),
    )

    async def on_submit(self, interaction: discord.Interaction):
        """フォーム送信時の処理"""
        await interaction.response.defer(ephemeral=True)  # noqa
        # ギルドとチャンネルの取得
        channel_division = await interaction.guild.fetch_channel(settings.channel_id.DIVISION)
        # フォームを送信したユーザーの情報を取得
        user = interaction.user
        server_name = user.display_name
        avatar = user.display_avatar.url
        # 分隊募集メッセージ（Embed）の作成
        embed = discord.Embed(title=f"分隊募集中！", color=0x0000ff)
        embed.add_field(name="1.日時", value=self.dtime.component.value, inline=False)  # noqa
        embed.add_field(name="2. Tier（オペレーションの場合は名称）", value=self.tier.component.value,
                        inline=False)  # noqa
        embed.add_field(name="3. 募集人数", value=self.member_count.component.value, inline=False)  # noqa
        embed.add_field(name="4. 初心者ですか？", value=self.newbie.component.values[0], inline=False)  # noqa
        if not self.other.component.value == "":  # noqa
            embed.add_field(name="5. その他注記事項", value=self.other.component.value, inline=False)  # noqa
        else:
            embed.add_field(name="5. その他注記事項", value="入力なし", inline=False)
        embed.set_author(name=f"{server_name}", icon_url=f"{avatar}")
        # 分隊募集メッセージを送信し、紐づくスレッドを作成
        message = await channel_division.send(f"<@&{settings.role_id.DIVISION}>", embed=embed)
        thread = await message.create_thread(name=f"{server_name} - 分隊募集")
        await thread.add_user(user)
        # フォームへのレスポンス
        response_embed = discord.Embed(description=f"ℹ️ <#{settings.channel_id.DIVISION}>に分隊募集を作成しました",
                                       color=COLOR_OK)
        await interaction.followup.send(embed=response_embed, ephemeral=True)
        # DBに保存
        action_datetime = time.time()
        await db.save_division_log(user.id, action_datetime)
        # ログの保存
        logger.info(f"{interaction.user.display_name}（UID：{interaction.user.id}）"
                    f"がフォーム「分隊募集」を使用しました。")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """エラー発生時の処理"""
        await discord_error(self.title, interaction, error, logger)


async def setup(bot):
    """起動時のコグへの追加"""
    await bot.add_cog(Division(bot))
    bot.add_view(view=DivisionView())
