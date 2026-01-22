from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

# Assuming DataManager, GameLogic, and Player are correctly defined and imported
from utils.data_manager import DataManager
from utils.game_logic import GameLogic
from models.player import Player

class GamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Initialize DataManager and GameLogic for persistent data handling and game mechanics
        self.data_manager = DataManager()
        self.game_logic = GameLogic()

    @app_commands.command(name="start_2", description="新しい冒険を開始し、専用のプライベートスレッドを作成します。")
    async def start(self, interaction: discord.Interaction):
        '''
        新しい冒険を開始し、ユーザー専用のプライベートスレッドを作成します。
        既存のゲームがある場合は、その旨を通知します。
        '''
        user_id = interaction.user.id

        # 1. ユーザーが既にアクティブなゲームを持っているかチェック
        player_data_dict = self.data_manager.get_player_data(user_id)
        if player_data_dict:
            player = Player.from_dict(player_data_dict)
            # 既存のスレッドがある場合は、そこへ誘導
            if player.current_thread_id:
                thread = self.bot.get_channel(player.current_thread_id) or await self.bot.fetch_channel(player.current_thread_id)
                if thread:
                    await interaction.response.send_message(
                        f"あなたは既に冒険中です！続きは{thread.mention}で行ってください。\n" +
                        "新しい冒険を始めるには、現在の冒険を終了する必要があります。（未実装）",
                        ephemeral=True
                    )
                    return
            # スレッド情報がないがプレイヤーデータはある場合
            await interaction.response.send_message(
                f"あなたの冒険データが見つかりました。しかし、紐付けられたスレッドが見つかりません。\n" +
                "新しいスレッドを作成して冒険を再開します。",
                ephemeral=True
            )
            # 既存のプレイヤーデータがあるがスレッドがない場合、新しいスレッドを作成して紐付け直す
            player = self.game_logic.initialize_player(user_id) # 新しいプレイヤーとして初期化

        else:
            # 2. アクティブなゲームがない場合、新しいプレイヤーキャラクターを初期化
            player = self.game_logic.initialize_player(user_id)

        # 3. ユーザー専用のプライベートスレッドを作成
        # スレッド名にユーザー名を含めることで、どのユーザーの冒険か分かりやすくする
        thread_name = f"{interaction.user.display_name}の冒険"
        try:
            # interaction.channelがTextChannelであることを期待
            if isinstance(interaction.channel, discord.TextChannel):
                thread = await interaction.channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.private_thread, # プライベートスレッド
                    reason=f"{interaction.user.display_name}の新しい冒険"
                )
            else:
                await interaction.response.send_message(
                    "このチャンネルでは冒険を開始できません。テキストチャンネルで試してください。",
                    ephemeral=True
                )
                return
        except discord.Forbidden:
            await interaction.response.send_message(
                "スレッドを作成する権限がありません。ボットに適切な権限を与えてください。",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.response.send_message(
                f"スレッドの作成中にエラーが発生しました: {e}",
                ephemeral=True
            )
            return

        # 4. 新しいプレイヤーデータにスレッドIDを保存
        player.current_thread_id = thread.id
        self.data_manager.update_player_data(user_id, player.to_dict())

        # 5. 新しく作成されたスレッドに初期のウェルカムメッセージとキャラクターのステータス概要を送信
        welcome_embed = discord.Embed(
            title="冒険の始まり！",
            description=f"{interaction.user.display_name}さん、新しい冒険へようこそ！\n" +
                        "このスレッドがあなたの冒険の舞台となります。",
            color=discord.Color.green()
        )
        welcome_embed.add_field(name="目標", value="10000m踏破を目指しましょう！", inline=False)
        welcome_embed.add_field(name="現在のステータス", value=player.get_status_string(), inline=False)
        welcome_embed.set_footer(text="/m コマンドで前進し、ダンジョンを探索しましょう！")

        await thread.send(embed=welcome_embed)

        # 6. 元のインタラクションに応答し、冒険が開始されたことと新しいスレッドへのリンクを通知
        await interaction.response.send_message(
            f"冒険が始まりました！あなたの冒険スレッドは {thread.mention} です。",
            ephemeral=True
        )

    @app_commands.command(name="m", description="ダンジョンを前進します。ランダムなイベントが発生します。")
    async def m(self, interaction: discord.Interaction):
        '''
        ダンジョンを前進し、ランダムなイベント（敵、アイテム、ストーリーなど）を発生させます。
        '''
        user_id = interaction.user.id

        # 1. ユーザーがアクティブなゲームを持っているかチェック
        player_data_dict = self.data_manager.get_player_data(user_id)
        if not player_data_dict:
            await interaction.response.send_message(
                "冒険を開始するには `/start` コマンドを使用してください。",
                ephemeral=True
            )
            return

        player = Player.from_dict(player_data_dict)

        # 2. プレイヤーが現在戦闘中ではないかチェック
        if player.in_combat:
            await interaction.response.send_message(
                "あなたは現在戦闘中です！ `/attack`, `/item`, `/run` のいずれかを使用してください。",
                ephemeral=True
            )
            return

        # 3. プレイヤーの現在のダンジョン状態とキャラクターデータを取得
        # スレッドが現在のインタラクションのチャンネルと一致するか確認
        if interaction.channel_id != player.current_thread_id:
            # ユーザーが間違った場所でコマンドを実行した場合、正しいスレッドへ誘導
            thread = self.bot.get_channel(player.current_thread_id) or await self.bot.fetch_channel(player.current_thread_id)
            if thread:
                await interaction.response.send_message(
                    f"このコマンドはあなたの冒険スレッド {thread.mention} で実行してください。",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "あなたの冒険スレッドが見つかりません。`/start` で新しい冒険を開始してください。",
                    ephemeral=True
                )
            return

        # 4. ダンジョンを前進させ、距離を更新
        player.distance += 1

        # 5. GameLogicを使用して次のダンジョンイベントを決定
        event = self.game_logic.generate_event(player)
        event_type = event.get("type")
        event_message = ""
        event_embed = discord.Embed(color=discord.Color.blue())

        if event_type == "monster":
            # モンスターとの遭遇
            monster = event.get("monster")
            player.in_combat = True
            player.current_monster = monster
            event_embed.title = f"⚔️ モンスター出現！ - {monster['name']}"
            event_embed.description = (
                f"{monster['name']}が現れた！\n" +
                f"HP: {monster['hp']}, ATK: {monster['attack']}, DEF: {monster['defense']}\n" +
                "どうする？ `/attack`, `/item`, `/run`"
            )
            event_embed.color = discord.Color.red()

        elif event_type == "item":
            # アイテムの発見
            item = event.get("item")
            player.inventory.append(item['name']) # アイテムをインベントリに追加
            event_embed.title = f"📦 アイテム発見！ - {item['name']}"
            event_embed.description = f"{item['name']}を見つけた！インベントリに追加されました。"
            event_embed.color = discord.Color.gold()

        elif event_type == "story":
            # ストーリーイベント
            event_embed.title = "📜 物語の断片"
            event_embed.description = event.get("message", "何かが起こった...")
            event_embed.color = discord.Color.purple()

        else: # empty or unknown event
            # 何も起こらない部屋
            event_embed.title = "🚶‍♂️ 静かな道"
            event_embed.description = event.get("message", "何も起こらなかった。静かな道のようだ。")
            event_embed.color = discord.Color.light_grey()

        event_embed.set_footer(text=f"現在地: {player.distance}m")

        # 6. 更新されたプレイヤーとダンジョンデータを保存
        self.data_manager.update_player_data(user_id, player.to_dict())

        # 7. プライベートアドベンチャースレッドにイベントの詳細メッセージを送信
        adventure_thread = self.bot.get_channel(player.current_thread_id)
        if adventure_thread:
            # 以前のイベントメッセージがある場合、それを編集して新しいイベントを追加する（オプション）
            # 今回はシンプルに新しいメッセージを送信
            sent_message = await adventure_thread.send(embed=event_embed)
            player.last_event_message_id = sent_message.id # 最後のイベントメッセージIDを保存
            self.data_manager.update_player_data(user_id, player.to_dict())
        else:
            # スレッドが見つからない場合はエラーを報告
            await interaction.followup.send(
                "冒険スレッドが見つかりませんでした。`/start` で新しい冒険を開始してください。",
                ephemeral=True
            )
            return

        # 8. 元のインタラクションに応答し、プレイヤーが移動したことを確認
        await interaction.response.send_message(
            f"ダンジョンを前進しました。現在地: {player.distance}m",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesCog(bot))