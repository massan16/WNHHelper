import discord
from discord import app_commands
from discord import ui
from discord.ext import commands

import api
import db
from config import COLOR_OK, COLOR_WARN, settings
from exception import discord_error
from logs import discord_logger as logger

logger = logger.getChild("newbie_role")


class Newbie(commands.Cog):
    """コマンド実装用のクラス"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def create_message(self, interaction: discord.Interaction):
        """初心者用ロール選択用メッセージの送信"""
        # ドロップダウンを含むビューを作成
        view = NewbieButton()
        # ビューを含むメッセージを送信
        channel = interaction.channel
        await channel.send(view=view)
        # コマンドへのレスポンス
        response_embed = discord.Embed(description="ℹ️ 送信が完了しました", color=COLOR_OK)
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  # noqa
        # ログの保存
        logger.info(f"{interaction.user.display_name}（UID：{interaction.user.id}）"
                    f"がコマンド「{interaction.command.name}」を使用しました。")

    @app_commands.command(description="初心者ロールの要件確認")
    @app_commands.checks.has_role(settings.role_id.WNH_STAFF)
    @app_commands.guilds(settings.GUILD_ID)
    @app_commands.guild_only()
    async def manual_check_newbie_role(self, interaction: discord.Interaction):
        """初心者用ロールの条件を満たしているかを手動確認"""
        await interaction.response.defer(ephemeral=True)  # noqa
        await self.check_newbie_role()
        # コマンドへのレスポンス
        response_embed = discord.Embed(description="ℹ️ 処理が完了しました", color=COLOR_OK)
        await interaction.followup.send(embed=response_embed, ephemeral=True)
        # ログの保存
        logger.info(f"{interaction.user.display_name}（UID：{interaction.user.id}）"
                    f"がコマンド「{interaction.command.name}」を使用しました。")

    async def check_newbie_role(self):
        """初心者用ロールの条件を満たしているか再確認"""
        # ギルドとロールの取得
        guild = self.bot.get_guild(settings.GUILD_ID)
        role_mattari = guild.get_role(settings.role_id.MATTARI)
        role_gatsu = guild.get_role(settings.role_id.GATSU)
        # まったりロールの確認
        for mattari_member in role_mattari.members:
            # DBからWargaming UIDを取得し代入
            user_info_result = await db.search_user(mattari_member.id)
            try:
                discord_id, account_id, region = user_info_result
            except ValueError:
                logger.error(f"{mattari_member.id}が認証を行っていない可能性があります。")
            else:
                # 戦闘数の照会と代入
                wg_api_result = await api.wows_user_info(account_id, region)
                nickname, battles = wg_api_result
                # 戦闘数が3001以上の場合ロールを解除
                if battles == "private" or battles > 3000:
                    await mattari_member.remove_roles(role_mattari, reason="定期資格審査による")
        # がつがつロールの確認
        for gatsu_member in role_gatsu.members:
            user_info_result = await db.search_user(gatsu_member.id)
            try:
                discord_id, account_id, region = user_info_result
            except ValueError:
                logger.error(f"{gatsu_member.id}が認証を行っていない可能性があります。")
            else:
                # 戦闘数の照会と代入
                wg_api_result = await api.wows_user_info(account_id, region)
                nickname, battles = wg_api_result
                # 戦闘数が3001以上の場合ロールを解除
                if battles == "private" or battles > 3000:
                    await gatsu_member.remove_roles(role_gatsu, reason="定期資格審査による")

    async def cog_app_command_error(self, interaction, error):
        """コマンド実行時のエラー処理"""
        await discord_error(interaction.command.name, interaction, error, logger)


class NewbieButton(ui.View):
    """初心者ロール取得ボタンの実装"""

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="まったり", emoji="🔵", style=discord.ButtonStyle.blurple, custom_id="mattari")  # noqa
    async def button_mattari(self, interaction: discord.Interaction, button: ui.Button):
        await role_mattari_callback(interaction, button)

    @ui.button(label="がつがつ", emoji="🟠", style=discord.ButtonStyle.blurple, custom_id="gatugatu")  # noqa
    async def button_gatsu(self, interaction: discord.Interaction, button: ui.Button):
        await role_gatsu_callback(interaction, button)


async def role_mattari_callback(interaction: discord.Interaction, button: ui.Button):
    """まったりロール用ボタン押下時の処理

    ボタン系はボタンのcallbackに直接書かず、別関数にすることによって処理内容変更後にボタンを再生成せずとも反映できる。
    """
    # ギルドとロールの取得
    role_mattari = interaction.guild.get_role(settings.role_id.MATTARI)
    role_gatsu = interaction.guild.get_role(settings.role_id.GATSU)
    # ボタンを押したユーザーの取得
    member = interaction.guild.get_member(interaction.user.id)
    # ロール保有状況の取得
    role = member.get_role(settings.role_id.MATTARI)
    # まったりロールを保有している場合は削除
    if role is not None:
        response_embed = discord.Embed(description=f"ℹ️ <@&{settings.role_id.MATTARI}>を削除しました。", color=COLOR_OK)
        await member.remove_roles(role_mattari, reason="初心者用ボタンによる")
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  # noqa
    else:
        await interaction.response.defer(ephemeral=True)  # noqa
        # DBからWargaming UIDを取得し代入
        user_info_result = await db.search_user(interaction.user.id)
        discord_id, account_id, region = user_info_result
        # 戦闘数の照会と代入
        wg_api_result = await api.wows_user_info(account_id, region)
        nickname, battles = wg_api_result
        # 戦績非公開の場合
        if battles == "private":
            # ボタンへのレスポンス
            response_embed = discord.Embed(description="⚠️ 戦績を公開にしてから再度お試しください。",
                                           color=COLOR_WARN)
            await interaction.followup.send(embed=response_embed, ephemeral=True)
        else:
            # 戦闘数が3000戦以上の場合
            if role is None and battles > 3000:
                # Embedの作成と送信
                response_embed = discord.Embed(description="⚠️ あなたは初心者ではありません。", color=COLOR_WARN)
                await interaction.followup.send(embed=response_embed, ephemeral=True)
            # 戦闘数が3000戦以下の場合
            elif role is None and battles <= 3000:
                # がつがつロールを保有している場合は削除
                await member.remove_roles(role_gatsu, reason="初心者用ボタンによる")
                # まったりロールを付与
                await member.add_roles(role_mattari, reason="初心者用ボタンによる")
                # ボタンへのレスポンス
                response_embed = discord.Embed(description=f"ℹ️ <@&{settings.role_id.MATTARI}>を付与しました。",
                                               color=COLOR_OK)
                await interaction.followup.send(embed=response_embed, ephemeral=True)


async def role_gatsu_callback(interaction: discord.Interaction, button: ui.Button):
    """がつがつロール用ボタン押下時の処理

    ボタン系はボタンのcallbackに直接書かず、別関数にすることによって処理内容変更後にボタンを再生成せずとも反映できる。
    """
    # ギルドとロールの取得
    role_mattari = interaction.guild.get_role(settings.role_id.MATTARI)
    role_gatsu = interaction.guild.get_role(settings.role_id.GATSU)
    # ボタンを押したユーザーの取得
    member = interaction.guild.get_member(interaction.user.id)
    # ロール保有状況の取得
    role = member.get_role(settings.role_id.GATSU)
    # がつがつロールを保有している場合は削除
    if role is not None:
        response_embed = discord.Embed(description=f"ℹ️ <@&{settings.role_id.GATSU}>を削除しました。", color=COLOR_OK)
        await member.remove_roles(role_gatsu, reason="初心者用ボタンによる")
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  # noqa
    else:
        await interaction.response.defer(ephemeral=True)  # noqa
        # DBからWargaming UIDを取得し代入
        user_info_result = await db.search_user(interaction.user.id)
        discord_id, account_id, region = user_info_result
        # 戦闘数の照会と代入
        wg_api_result = await api.wows_user_info(account_id, region)
        nickname, battles = wg_api_result
        # 戦績非公開の場合
        if battles == "private":
            # ボタンへのレスポンス
            response_embed = discord.Embed(description="⚠️ 戦績を公開にしてから再度お試しください。",
                                           color=COLOR_WARN)
            await interaction.followup.send(embed=response_embed, ephemeral=True)
        else:
            # 戦闘数が3000戦以上の場合
            if role is None and battles >= 3000:
                response_embed = discord.Embed(description="⚠️ あなたは初心者ではありません。", color=COLOR_WARN)
                await interaction.followup.send(embed=response_embed, ephemeral=True)
            # 戦闘数が3000戦以下の場合
            elif role is None and battles < 3000:
                # まったりロールを保有している場合は削除
                await member.remove_roles(role_mattari, reason="初心者用ボタンによる")
                # がつがつロールを付与
                await member.add_roles(role_gatsu, reason="初心者用ボタンによる")
                # ボタンへのレスポンス
                response_embed = discord.Embed(description=f"ℹ️ <@&{settings.role_id.GATSU}>を付与しました。",
                                               color=COLOR_OK)
                await interaction.followup.send(embed=response_embed, ephemeral=True)


async def setup(bot):
    """起動時のコグへの追加"""
    await bot.add_cog(Newbie(bot))
    bot.add_view(view=NewbieButton())
