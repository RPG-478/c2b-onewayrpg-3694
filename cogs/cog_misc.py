from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
import random # For run command's random chance, if not fully handled by GameLogic

# Import utility modules as per blueprint
from utils.data_manager import DataManager
from utils.game_logic import GameLogic
from models.player import Player # Assuming Player model might be used for type hinting or data structure
from models.dungeon import Monster # Assuming Monster model might be used

# Define a View for item selection
class ItemSelectView(discord.ui.View):
    """
    戦闘中に使用するアイテムを選択するためのView。
    プレイヤーのインベントリから選択肢を動的に生成します。
    """
    def __init__(self, player_id: str, data_manager: DataManager, game_logic: GameLogic, timeout=180):
        super().__init__(timeout=timeout)
        self.player_id = player_id
        self.data_manager = data_manager
        self.game_logic = game_logic
        self.selected_item = None # To store the selected item name
        self.message = None # To store the message this view is attached to, for later editing

    @discord.ui.select(
        placeholder="使用するアイテムを選択してください...",
        min_values=1,
        max_values=1,
        options=[] # This will be populated dynamically in the item command
    )
    async def select_item_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        """
        アイテムが選択されたときに呼び出されるコールバック。
        選択されたアイテム名を保存し、Viewを停止します。
        """
        # Ensure only the player who initiated the command can interact with this specific view
        if str(interaction.user.id) != self.player_id:
            await interaction.response.send_message("このメニューはあなたのためのものではありません。", ephemeral=True)
            return

        self.selected_item = select.values[0]
        await interaction.response.defer() # Defer the interaction to show thinking state
        self.stop() # Stop the view, signaling that an item has been selected

    async def on_timeout(self) -> None:
        """
        Viewがタイムアウトしたときに呼び出されます。
        """
        # Disable all items if the view times out
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                item.disabled = True
        # Update the message to reflect timeout and disable the view
        if self.message:
            await self.message.edit(content="アイテム選択の時間が終了しました。", view=self)

class CombatCog(commands.Cog):
    """
    戦闘関連のコマンド（攻撃、アイテム使用、逃走）を管理するCog。
    """
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data_manager = DataManager()
        self.game_logic = GameLogic()

    async def _send_combat_update_embed(self, interaction: discord.Interaction, player_data: dict, monster_data: dict, description: str, color: discord.Color = discord.Color.blue()) -> None:
        """
        戦闘状況を更新するEmbedを送信するヘルパー関数。
        """
        embed = discord.Embed(
            title="⚔️ 戦闘状況",
            description=description,
            color=color
        )
        # プレイヤー情報
        embed.add_field(name="あなた", value=f"HP: {player_data.get('hp', 0)}/{player_data.get('max_hp', 0)}", inline=True)
        # モンスター情報
        embed.add_field(name=f"敵: {monster_data.get('name', 'Unknown')}", value=f"HP: {monster_data.get('hp', 0)}/{monster_data.get('max_hp', 0)}", inline=True)
        embed.set_footer(text=f"距離: {player_data.get('distance', 0)}m | レベル: {player_data.get('level', 1)}")
        await interaction.followup.send(embed=embed) # Use followup as initial interaction might be deferred

    async def _handle_monster_defeat(self, interaction: discord.Interaction, player_id: str, player_data: dict, monster_data: dict) -> str:
        """
        モンスター撃破時の処理を行い、結果メッセージを返す。
        経験値獲得、アイテムドロップ、戦闘状態の解除など。
        """
        # モンスター撃破時のロジックをGameLogicに委譲
        loot_message, level_up_message = self.game_logic.handle_monster_defeat(player_data, monster_data)

        # 戦闘状態を解除
        player_data['in_combat'] = False
        player_data['current_monster'] = None

        # データ保存
        await self.data_manager.save_player_data(player_id, player_data)

        # 結果メッセージを構築
        result_message = f"モンスター「{monster_data['name']}」を倒した！\n{loot_message}"
        if level_up_message:
            result_message += f"\n{level_up_message}"
        return result_message

    async def _handle_player_defeat(self, interaction: discord.Interaction, player_id: str, player_data: dict) -> str:
        """
        プレイヤー敗北時の処理を行い、結果メッセージを返す。
        ゲームオーバー処理、プレイヤーデータの初期化など。
        """
        # プレイヤー敗北時のロジックをGameLogicに委譲
        game_over_message = self.game_logic.handle_game_over(player_data)

        # 戦闘状態を解除
        player_data['in_combat'] = False
        player_data['current_monster'] = None

        # プレイヤーデータをリセットまたは初期化（ゲームオーバー処理）
        # 例: 距離を0に戻し、HPを最大にし、インベントリを初期化
        player_data['hp'] = player_data['max_hp'] # HPを最大値に戻す
        player_data['distance'] = 0 # 進行距離をリセット
        player_data['inventory'] = [] # インベントリを初期化
        player_data['equipment'] = {} # 装備をリセット
        player_data['exp'] = 0 # 経験値をリセット
        player_data['level'] = 1 # レベルをリセット
        player_data['atk'] = 10 # 基本攻撃力をリセット
        player_data['def'] = 5 # 基本防御力をリセット

        # データ保存
        await self.data_manager.save_player_data(player_id, player_data)

        return game_over_message

    @app_commands.command(name="attack", description="戦闘中に敵を攻撃します。")
    async def attack(self, interaction: discord.Interaction) -> None:
        """
        戦闘中に敵を攻撃し、ダメージ計算と戦闘状況の更新を行います。
        モンスターのHPが0になった場合は撃破処理、プレイヤーのHPが0になった場合はゲームオーバー処理を行います。
        """
        await interaction.response.defer() # コマンド応答を遅延させ、処理中に「考え中...」を表示

        player_id = str(interaction.user.id)
        player_data = await self.data_manager.load_player_data(player_id)

        # プレイヤーデータが存在しない場合は、ゲームを開始していない旨を伝える
        if not player_data:
            await interaction.followup.send("冒険を開始していません。`/start`コマンドで新しい冒険を始めましょう！", ephemeral=True)
            return

        # 戦闘中かどうかのチェック
        if not player_data.get('in_combat'):
            await interaction.followup.send("現在、戦闘中ではありません。", ephemeral=True)
            return

        monster_data = player_data.get('current_monster')
        if not monster_data: # 念のため、モンスターデータがない場合も考慮
            await interaction.followup.send("戦闘中のモンスターデータが見つかりません。戦闘状態をリセットしました。", ephemeral=True)
            player_data['in_combat'] = False
            await self.data_manager.save_player_data(player_id, player_data)
            return

        # プレイヤーの攻撃
        damage_dealt = self.game_logic.calculate_damage(player_data, monster_data)
        monster_data['hp'] = max(0, monster_data['hp'] - damage_dealt) # HPが0未満にならないようにする

        description = f"⚔️ あなたは{monster_data['name']}に**{damage_dealt}**ダメージを与えた！\n"

        if monster_data['hp'] <= 0:
            # モンスター撃破処理
            description += await self._handle_monster_defeat(interaction, player_id, player_data, monster_data)
            await self._send_combat_update_embed(interaction, player_data, monster_data, description, discord.Color.green())
            return # 戦闘終了のため、ここで処理を終える

        # モンスターがまだ生きている場合、反撃
        monster_damage = self.game_logic.calculate_monster_attack(monster_data, player_data)
        player_data['hp'] = max(0, player_data['hp'] - monster_damage) # HPが0未満にならないようにする
        description += f"👹 {monster_data['name']}はあなたに**{monster_damage}**ダメージを与えた！\n"

        if player_data['hp'] <= 0:
            # プレイヤー敗北処理
            description += await self._handle_player_defeat(interaction, player_id, player_data)
            await self._send_combat_update_embed(interaction, player_data, monster_data, description, discord.Color.red())
            return # ゲームオーバーのため、ここで処理を終える

        # 戦闘継続の場合、データを保存
        player_data['current_monster'] = monster_data # 更新されたモンスターデータを保存
        await self.data_manager.save_player_data(player_id, player_data)

        # 戦闘状況をEmbedで表示
        await self._send_combat_update_embed(interaction, player_data, monster_data, description)


    @app_commands.command(name="item", description="戦闘中にアイテムを使用します。")
    async def item(self, interaction: discord.Interaction) -> None:
        """
        戦闘中にアイテムを使用するための選択メニューを表示し、選択されたアイテムの効果を適用します。
        アイテム使用後、モンスターが反撃します。
        """
        await interaction.response.defer(ephemeral=True) # コマンド応答を遅延させ、処理中に「考え中...」を表示（ユーザーにだけ見せる）

        player_id = str(interaction.user.id)
        player_data = await self.data_manager.load_player_data(player_id)

        if not player_data:
            await interaction.followup.send("冒険を開始していません。`/start`コマンドで新しい冒険を始めましょう！", ephemeral=True)
            return

        if not player_data.get('in_combat'):
            await interaction.followup.send("現在、戦闘中ではありません。", ephemeral=True)
            return

        # 使用可能なアイテムをフィルタリング
        usable_items = [
            item for item in player_data.get('inventory', [])
            if item.get('quantity', 0) > 0 and self.game_logic.is_item_usable_in_combat(item.get('name'), player_data)
        ]

        if not usable_items:
            await interaction.followup.send("戦闘中に使用できるアイテムがありません。", ephemeral=True)
            return

        # Selectメニューのオプションを作成
        select_options = []
        for item in usable_items:
            select_options.append(discord.SelectOption(
                label=f"{item['name']} ({item['quantity']})",
                value=item['name'],
                description=f"{item.get('description', '効果不明')}"
            ))
            # DiscordのSelectOptionの最大数は25なので、それ以上は切り捨てる
            if len(select_options) >= 25:
                break

        # ItemSelectViewを作成し、オプションを動的に設定
        view = ItemSelectView(player_id, self.data_manager, self.game_logic)
        view.children[0].options = select_options # SelectコンポーネントはViewの最初のchild

        # アイテム選択メッセージを送信
        message = await interaction.followup.send("使用するアイテムを選択してください。", view=view, ephemeral=True)
        view.message = message # Store message to edit later if needed

        # ユーザーがアイテムを選択するのを待つ
        await view.wait()

        if view.selected_item:
            selected_item_name = view.selected_item
            description = ""
            monster_data = player_data.get('current_monster')

            # アイテム効果を適用
            item_effect_message = self.game_logic.apply_item_effect(selected_item_name, player_data)
            description += f"🧪 あなたは**{selected_item_name}**を使用した！\n{item_effect_message}\n"

            # アイテムを消費
            self.game_logic.consume_item(selected_item_name, player_data)

            # データ保存
            await self.data_manager.save_player_data(player_id, player_data)

            # モンスターの反撃
            if monster_data and player_data.get('hp', 0) > 0: # プレイヤーがまだ生きている場合のみ
                monster_damage = self.game_logic.calculate_monster_attack(monster_data, player_data)
                player_data['hp'] = max(0, player_data['hp'] - monster_damage)
                description += f"👹 {monster_data['name']}はあなたに**{monster_damage}**ダメージを与えた！\n"

                if player_data['hp'] <= 0:
                    # プレイヤー敗北処理
                    description += await self._handle_player_defeat(interaction, player_id, player_data)
                    await self._send_combat_update_embed(interaction, player_data, monster_data, description, discord.Color.red())
                    # 元のEphemeralメッセージを編集してViewを無効化
                    await message.edit(content="アイテム選択済み。", view=None)
                    return # ゲームオーバーのため、ここで処理を終える
                
                # 更新されたモンスターデータを保存
                player_data['current_monster'] = monster_data
                await self.data_manager.save_player_data(player_id, player_data)

            # 戦闘状況をEmbedで表示 (ephemeral=Falseで全体に表示されるようにする)
            await interaction.followup.send(embed=discord.Embed(
                title="⚔️ 戦闘状況 - アイテム使用",
                description=description,
                color=discord.Color.gold()
            ))
            # 元のEphemeralメッセージを編集してViewを無効化
            await message.edit(content="アイテム選択済み。", view=None)

        else:
            # タイムアウトまたはキャンセルされた場合
            await interaction.followup.send("アイテム選択がキャンセルされました。", ephemeral=True)
            await message.edit(content="アイテム選択がキャンセルされました。", view=None)


    @app_commands.command(name="run", description="戦闘から逃走を試みます。失敗することもあります。")
    async def run(self, interaction: discord.Interaction) -> None:
        """
        戦闘から逃走を試みます。成功または失敗し、結果に応じて処理が分岐します。
        失敗した場合はモンスターの反撃を受けます。
        """
        await interaction.response.defer() # コマンド応答を遅延させ、処理中に「考え中...」を表示

        player_id = str(interaction.user.id)
        player_data = await self.data_manager.load_player_data(player_id)

        if not player_data:
            await interaction.followup.send("冒険を開始していません。`/start`コマンドで新しい冒険を始めましょう！", ephemeral=True)
            return

        if not player_data.get('in_combat'):
            await interaction.followup.send("現在、戦闘中ではありません。", ephemeral=True)
            return

        monster_data = player_data.get('current_monster')
        if not monster_data:
            await interaction.followup.send("戦闘中のモンスターデータが見つかりません。戦闘状態をリセットしました。", ephemeral=True)
            player_data['in_combat'] = False
            await self.data_manager.save_player_data(player_id, player_data)
            return

        # 逃走判定
        escape_successful, escape_message = self.game_logic.attempt_escape(player_data, monster_data)
        description = f"🏃 {escape_message}\n"

        if escape_successful:
            # 逃走成功
            player_data['in_combat'] = False
            player_data['current_monster'] = None
            await self.data_manager.save_player_data(player_id, player_data)
            await self._send_combat_update_embed(interaction, player_data, monster_data, description, discord.Color.green())
        else:
            # 逃走失敗、モンスターの反撃
            monster_damage = self.game_logic.calculate_monster_attack(monster_data, player_data)
            player_data['hp'] = max(0, player_data['hp'] - monster_damage)
            description += f"👹 {monster_data['name']}の追撃により**{monster_damage}**ダメージを受けた！\n"

            if player_data['hp'] <= 0:
                # プレイヤー敗北処理
                description += await self._handle_player_defeat(interaction, player_id, player_data)
                await self._send_combat_update_embed(interaction, player_data, monster_data, description, discord.Color.red())
                return # ゲームオーバーのため、ここで処理を終える

            # 戦闘継続の場合、データを保存
            player_data['current_monster'] = monster_data # 更新されたモンスターデータを保存
            await self.data_manager.save_player_data(player_id, player_data)
            await self._send_combat_update_embed(interaction, player_data, monster_data, description, discord.Color.red())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CombatCog(bot))