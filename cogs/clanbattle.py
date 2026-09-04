import discord
from discord import ui
from discord.ext import commands

from bot import DISALLOW_MENTION
from config import COLOR_OK, COLOR_ERROR, settings
from exception import discord_error
from logs import discord_logger as logger

logger = logger.getChild("clanbattle")


class ClanBattle(commands.Cog):
    """コマンド実装用のクラス"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def create_message(self, interaction: discord.Interaction):
        """傭兵募集案内メッセージを送信"""
        # ビューを含むメッセージを送信
        channel = interaction.channel
        await channel.send(view=CBView(), allowed_mentions=DISALLOW_MENTION)
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


class CBView(ui.LayoutView):
    """分隊募集方法案内メッセージ"""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    text1 = ui.TextDisplay("## 傭兵募集について\n"
                           "当サーバーでの傭兵への応募は次の手順でご利用いただけます\n")
    text2 = ui.TextDisplay("### 応募方法1 既存の募集への応募\n"
                           f"1. <#{settings.channel_id.CLANBATTLE}>から応募したい募集を探し、応募ボタンを押してください。\n"
                           f"2. 作成されるスレッドからリクルーターとやりとりしてください。"
                           "### 応募方法2 応募したい募集がない場合\n"
                           "1. 下のボタンを押して応募フォームを開きます\n"
                           "2. <#{settings.channel_id.CLANBATTLE}>にプライベートスレッドが作成されますので、注視して下さい。")
    text3 = ui.TextDisplay("### 傭兵募集通知について\n"
                           "傭兵募集の通知が欲しい人は下のボタンを押すと専用ロールが付与されます\n"
                           "不要になった場合は再度押して下さい。")
    container = ui.Container(text1, text2, text3)

    action_row = ui.ActionRow()

    @action_row.button(label="傭兵募集通知ロールの取得/解除", emoji="🤝", style=discord.ButtonStyle.blurple,  # noqa
                       custom_id="cb_role")  # noqa
    async def cb_role_button(self, interaction: discord.Interaction, button: ui.Button):
        await cb_role_button_callback(interaction, button)

    @action_row.button(label="傭兵として参加する", style=discord.ButtonStyle.blurple,  # noqa
                       custom_id="cb_join_form")
    async def cb_join_form_button(self, interaction: discord.Interaction, button: ui.Button):
        await cb_join_form_button_callback(interaction, button)

    @action_row.button(label="傭兵を募集する", style=discord.ButtonStyle.blurple,  # noqa
                       custom_id="cb_invite_form")
    async def cb_invite_form_button(self, interaction: discord.Interaction, button: ui.Button):
        await cb_invite_form_button_callback(interaction, button)


class CBJoinButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="この募集に応募する", style=discord.ButtonStyle.blurple,  # noqa
                       custom_id="cb_join")
    async def cb_join_button(self, interaction: discord.Interaction, button: ui.Button):
        await cb_join_button_callback(interaction, button)


async def cb_role_button_callback(interaction: discord.Interaction, button: ui.Button):
    """分隊ロール取得/削除ボタンの処理

    ボタン系はボタンのcallbackに直接書かず、別関数にすることによって処理内容変更後にボタンを再生成せずとも反映できる。
    """
    # ロールを取得
    cb_role = interaction.guild.get_role(settings.role_id.CLANBATTLE)
    role = interaction.user.get_role(settings.role_id.CLANBATTLE)
    # ロールがある場合は削除
    if role is not None:
        response_embed = discord.Embed(description=f"ℹ️ <@&{settings.role_id.CLANBATTLE}>を削除しました。",
                                       color=COLOR_OK)
        await interaction.user.remove_roles(cb_role, reason="分隊ロールボタンによる")
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  # noqa
    # ロールがない場合は追加
    else:
        response_embed = discord.Embed(description=f"ℹ️ <@&{settings.role_id.CLANBATTLE}>を取得しました。",
                                       color=COLOR_OK)
        await interaction.user.add_roles(cb_role, reason="分隊ロールボタンによる")
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  # noqa


async def cb_invite_form_button_callback(interaction: discord.Interaction, button: ui.Button):
    """傭兵募集ボタンの処理

    ボタン系はボタンのcallbackに直接書かず、別関数にすることによって処理内容変更後にボタンを再生成せずとも反映できる。
    """
    if interaction.user.get_role(settings.role_id.CLAN_RECRUITER) is None:
        error_embed = discord.Embed(description=f"⚠️ この機能は<@&{settings.role_id.CLAN_RECRUITER}>のみ利用できます>", color=COLOR_ERROR)
        await interaction.response.send_message(embed=error_embed, ephemeral=True)  # noqa
    if interaction.user.is_timed_out():
        error_embed = discord.Embed(description="⚠️ タイムアウト中は利用できません", color=COLOR_ERROR)
        await interaction.response.send_message(embed=error_embed, ephemeral=True)  # noqa
    else:
        # フォームの呼び出し
        await interaction.response.send_modal(CB_Invite_Form())  # noqa


async def cb_join_form_button_callback(interaction: discord.Interaction, button: ui.Button):
    """傭兵応募ボタン（フォーム）の処理

    ボタン系はボタンのcallbackに直接書かず、別関数にすることによって処理内容変更後にボタンを再生成せずとも反映できる。
    """
    if interaction.user.is_timed_out():
        error_embed = discord.Embed(description="⚠️ タイムアウト中は利用できません", color=COLOR_ERROR)
        await interaction.response.send_message(embed=error_embed, ephemeral=True)  # noqa
    else:
        # フォームの呼び出し
        await interaction.response.send_modal(CB_Join_Form())  # noqa


async def cb_join_button_callback(interaction: discord.Interaction, button: ui.Button):
    """傭兵応募ボタンの処理

    ボタン系はボタンのcallbackに直接書かず、別関数にすることによって処理内容変更後にボタンを再生成せずとも反映できる。
    """
    if interaction.user.is_timed_out():
        error_embed = discord.Embed(description="⚠️ タイムアウト中は利用できません", color=COLOR_ERROR)
        await interaction.response.send_message(embed=error_embed, ephemeral=True)  # noqa
    else:
        # スレッドの作成
        thread = await interaction.channel.create_thread(name=f"応募 - {interaction.user.display_name}")
        recruiter_id_str = interaction.message.embeds[0].footer.text
        await thread.send(f"<@{recruiter_id_str}>\n"
                          f"<@{interaction.user.id}>さんが下記の募集に参加を希望しています。このスレッドでやりとりしてください。")
        await interaction.message.forward(thread)
        response_embed = discord.Embed(description=f"ℹ️ {thread.jump_url}からリクルーターとやりとりしてください。",
                                       color=COLOR_OK)
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  # noqa


class CB_Invite_Form(ui.Modal, title="分隊募集フォーム"):
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

    clantag = ui.Label(
        text="2.クランタグ",
        component=ui.TextInput(
            max_length=30,
        ),
    )

    vc = discord.ui.Label(
        text="3.VCの要否",
        component=discord.ui.Select(
            options=[
                discord.SelectOption(label="必須"),
                discord.SelectOption(label="聞き専可"),
                discord.SelectOption(label="不問"),
            ],
        ),
    )

    other = ui.Label(
        text="4.その他注記事項（無回答でもOK）",
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
        channel_cb = await interaction.guild.fetch_channel(settings.channel_id.CLANBATTLE)
        # フォームを送信したユーザーの情報を取得
        user = interaction.user
        server_name = user.display_name
        avatar = user.display_avatar.url
        clan_tag = self.clantag.component.value  # noqa
        # 分隊募集メッセージ（Embed）の作成
        embed = discord.Embed(title=f"傭兵募集中！ - {clan_tag}", color=0x0000ff)
        embed.add_field(name="1. 日時", value=self.dtime.component.value, inline=False)  # noqa
        embed.add_field(name="2. クランタグ", value=self.clantag.component.value,  # noqa
                        inline=False)  # noqa
        embed.add_field(name="3. VCの要否", value=self.vc.component.values[0], inline=False)  # noqa
        if not self.other.component.value == "":  # noqa
            embed.add_field(name="4. その他注記事項", value=self.other.component.value, inline=False)  # noqa
        else:
            embed.add_field(name="4. その他注記事項", value="入力なし", inline=False)
        embed.set_footer(text=f"{user.id}")
        # 傭兵募集メッセージを送信
        await channel_cb.send(f"<@&{settings.role_id.CLANBATTLE}>", embed=embed, view=CBJoinButton())
        # フォームへのレスポンス
        response_embed = discord.Embed(description=f"ℹ️ <#{settings.channel_id.CLANBATTLE}>に傭兵募集を作成しました",
                                       color=COLOR_OK)
        await interaction.followup.send(embed=response_embed, ephemeral=True)
        # ログの保存
        logger.info(f"{interaction.user.display_name}（UID：{interaction.user.id}）"
                    f"がフォーム「分隊募集」を使用しました。")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """エラー発生時の処理"""
        await discord_error(self.title, interaction, error, logger)


class CB_Join_Form(ui.Modal, title="分隊募集フォーム"):
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

    ign = ui.Label(
        text="2.IGN",
        component=ui.TextInput(
            max_length=30,
        ),
    )

    vc = discord.ui.Label(
        text="3.VCの可否",
        component=discord.ui.Select(
            options=[
                discord.SelectOption(label="可"),
                discord.SelectOption(label="聞き専"),
                discord.SelectOption(label="不可"),
            ],
        ),
    )

    other = ui.Label(
        text="4.その他注記事項（無回答でもOK）",
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
        channel_cb = await interaction.guild.fetch_channel(settings.channel_id.CLANBATTLE)
        # フォームを送信したユーザーの情報を取得
        user = interaction.user
        server_name = user.display_name
        avatar = user.display_avatar.url
        # 分隊募集メッセージ（Embed）の作成
        embed = discord.Embed(title=f"傭兵応募先募集中！ - {self.ign.component.value}", color=0x0000ff) # noqa
        embed.add_field(name="1. 日時", value=self.dtime.component.value, inline=False)  # noqa
        embed.add_field(name="2. IGN", value=self.ign.component.value,  # noqa
                        inline=False)  # noqa
        embed.add_field(name="3. VCの可否", value=self.vc.component.values[0], inline=False)  # noqa
        if not self.other.component.value == "":  # noqa
            embed.add_field(name="4. その他注記事項", value=self.other.component.value, inline=False)  # noqa
        else:
            embed.add_field(name="4. その他注記事項", value="入力なし", inline=False)
        embed.set_author(name=f"{server_name}", icon_url=f"{avatar}")
        # 傭兵先募集スレッドを作成
        thread = await channel_cb.create_thread(name=f"募集 - {interaction.user.display_name}")
        await thread.send(f"<@&{settings.role_id.CLAN_RECRUITER}>\n"
                          f"<@{interaction.user.id}>さんが傭兵先を募集しています。このスレッドでやりとりしてください。", embed=embed)
        # フォームへのレスポンス
        response_embed = discord.Embed(description=f"ℹ️ {thread.jump_url}>に傭兵先募集を作成しました。",
                                       color=COLOR_OK)
        await interaction.followup.send(embed=response_embed, ephemeral=True)
        # ログの保存
        logger.info(f"{interaction.user.display_name}（UID：{interaction.user.id}）"
                    f"がフォーム「分隊募集」を使用しました。")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """エラー発生時の処理"""
        await discord_error(self.title, interaction, error, logger)


async def setup(bot):
    """起動時のコグへの追加"""
    await bot.add_cog(ClanBattle(bot))
    bot.add_view(view=CBView())
    bot.add_view(view=CBJoinButton())
