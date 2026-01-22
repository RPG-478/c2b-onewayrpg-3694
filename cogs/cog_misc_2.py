from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands
from utils.data_manager import DataManager
from models.player import Player, Item # Assuming Item is also defined in models/player.py

class CogMisc2Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_manager = DataManager() # Data manager instance for loading/saving player data

    # Temporary /start command for testing purposes, ideally this would be in cogs/game.py
    @app_commands.command(name="start", description="新しい冒険を開始し、専用のプライベートスレッドを作成します。")
    async def start(self, interaction: discord.Interaction):
        """
        新しい冒険を開始し、プレイヤーデータを初期化します。
        既にデータがある場合は、そのデータをロードします。
        """
        player_id = interaction.user.id
        player = await self.data_manager.load_player_data(player_id)

        if player:
            await interaction.response.send_message(
                f"既に冒険が始まっています、{player.name}！現在の進行距離は {player.distance}m です。",
                ephemeral=True
            )
        else:
            # 新しいプレイヤーを作成
            player = await self.data_manager.create_new_player(player_id, interaction.user.display_name)
            await interaction.response.send_message(
                f"新しい冒険が始まりました、{player.name}！ダンジョンに挑みましょう！\n"
                f"初期装備として「{player.inventory[0].name}」と「{player.inventory[1].name}」を手に入れました。",
                ephemeral=True
            )
            # In a real scenario, this would also create a private thread.
            # For this implementation, we'll skip thread creation as it's not directly requested for this cog.


    @app_commands.command(name="inventory", description="所持しているアイテムと現在装備中のアイテム一覧を表示します。")
    async def inventory(self, interaction: discord.Interaction):
        '''プレイヤーのインベントリと装備品を表示します。'''
        player_id = interaction.user.id
        player = await self.data_manager.load_player_data(player_id)

        # プレイヤーデータが存在しない場合は、/startコマンドを促す
        if not player:
            await interaction.response.send_message(
                "冒険が始まっていません。`/start` コマンドで新しい冒険を開始してください。",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🎒 {player.name} のインベントリ",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # 装備品セクション
        equipped_items_str = ""
        weapon_item = player.equipped_items.get("weapon")
        armor_item = player.equipped_items.get("armor")

        equipped_items_str += f"**武器**: {weapon_item.name} (ATK+{weapon_item.value})\n" if weapon_item else "**武器**: なし\n"
        equipped_items_str += f"**防具**: {armor_item.name} (DEF+{armor_item.value})\n" if armor_item else "**防具**: なし\n"
        
        embed.add_field(name="現在装備中", value=equipped_items_str, inline=False)

        # 所持品セクション
        if player.inventory:
            # アイテムを種類ごとに分類
            consumables = [item for item in player.inventory if item.item_type == "consumable"]
            equipment = [item for item in player.inventory if item.item_type in ["weapon", "armor"]]

            inventory_str = ""
            if consumables:
                inventory_str += "**消耗品:**\n"
                for item in consumables:
                    inventory_str += f"- {item.name} ({item.description})\n"
            if equipment:
                inventory_str += "\n**装備品:**\n"
                for item in equipment:
                    inventory_str += f"- {item.name} ({item.description}) "
                    if item.item_type == "weapon":
                        inventory_str += f"(ATK+{item.value})\n"
                    elif item.item_type == "armor":
                        inventory_str += f"(DEF+{item.value})\n"
                    else:
                        inventory_str += "\n"
            if not inventory_str: # Should not happen if player.inventory is not empty, but good for safety
                inventory_str = "インベントリは空です。"
        else:
            inventory_str = "インベントリは空です。"
        
        embed.add_field(name="所持品", value=inventory_str, inline=False)
        embed.set_footer(text="装備したい場合は /equip コマンドを使用してください。")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="equip", description="所持している装備品を装備します。")
    @app_commands.describe(item_name="装備したいアイテムの名前")
    async def equip(self, interaction: discord.Interaction, item_name: str):
        '''プレイヤーが所持している装備品を装備します。'''
        player_id = interaction.user.id
        player = await self.data_manager.load_player_data(player_id)

        # プレイヤーデータが存在しない場合は、/startコマンドを促す
        if not player:
            await interaction.response.send_message(
                "冒険が始まっていません。`/start` コマンドで新しい冒険を開始してください。",
                ephemeral=True
            )
            return

        # インベントリからアイテムを検索 (大文字小文字を区別しない)
        target_item: Item | None = None
        for item in player.inventory:
            if item.name.lower() == item_name.lower():
                target_item = item
                break

        if not target_item:
            await interaction.response.send_message(
                f"「{item_name}」はインベントリに見つかりませんでした。",
                ephemeral=True
            )
            return

        # アイテムが装備可能かチェック
        if target_item.item_type not in ["weapon", "armor"] or not target_item.slot:
            await interaction.response.send_message(
                f"「{target_item.name}」は装備できるアイテムではありません。",
                ephemeral=True
            )
            return

        # 既に同じアイテムが装備されているかチェック
        if player.equipped_items[target_item.slot] and player.equipped_items[target_item.slot].name.lower() == target_item.name.lower():
            await interaction.response.send_message(
                f"「{target_item.name}」は既に装備されています。",
                ephemeral=True
            )
            return

        # 既存の装備品をインベントリに戻す
        old_item = player.equipped_items[target_item.slot]
        if old_item:
            player.inventory.append(old_item) # 古い装備をインベントリに戻す
            player.equipped_items[target_item.slot] = None # スロットを空にする

        # 新しいアイテムを装備
        player.equipped_items[target_item.slot] = target_item
        player.inventory.remove(target_item) # インベントリから装備したアイテムを削除

        # プレイヤーデータを保存
        await self.data_manager.save_player_data(player)

        # 成功メッセージ
        response_message = f"✅ 「{target_item.name}」を{target_item.slot}に装備しました！"
        if old_item:
            response_message += f"\n「{old_item.name}」はインベントリに戻されました。"

        await interaction.response.send_message(response_message, ephemeral=True)

    @app_commands.command(name="status", description="現在のキャラクターのステータス（HP, ATK, DEF）と進行距離を表示します。")
    async def status(self, interaction: discord.Interaction):
        '''プレイヤーの現在のステータスと進行距離を表示します。'''
        player_id = interaction.user.id
        player = await self.data_manager.load_player_data(player_id)

        # プレイヤーデータが存在しない場合は、/startコマンドを促す
        if not player:
            await interaction.response.send_message(
                "冒険が始まっていません。`/start` コマンドで新しい冒険を開始してください。",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"👤 {player.name} のステータス",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # 基本ステータス
        embed.add_field(name="HP", value=f"{player.hp}/{player.max_hp}", inline=True)
        embed.add_field(name="攻撃力 (ATK)", value=f"{player.atk}", inline=True)
        embed.add_field(name="防御力 (DEF)", value=f"{player.def_val}", inline=True) # Using def_val to avoid keyword conflict

        # 進行距離
        embed.add_field(name="進行距離", value=f"{player.distance}m", inline=False)

        # 装備品サマリー
        equipped_summary = ""
        weapon = player.equipped_items.get("weapon")
        armor = player.equipped_items.get("armor")

        equipped_summary += f"武器: {weapon.name} (ATK+{weapon.value})" if weapon else "武器: なし"
        equipped_summary += "\n"
        equipped_summary += f"防具: {armor.name} (DEF+{armor.value})" if armor else "防具: なし"
        
        embed.add_field(name="装備品", value=equipped_summary, inline=False)
        embed.set_footer(text="装備品はATK/DEFに影響します。")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CogMisc2Cog(bot))