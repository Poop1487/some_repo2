import discord
from dotenv import load_dotenv
import os
import json
from flask import Flask
import asyncio
from threading import Thread
from google import generativeai as genai
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient

uri = "mongodb+srv://poopooops1488:2mjHYEfGpMeVDc0S@xp.exi9hjl.mongodb.net/?retryWrites=true&w=majority&appName=XP"

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

url = "https://citadel-hnll.onrender.com"

client = AsyncIOMotorClient(
    uri,
    tls=True,
    tlsAllowInvalidCertificates=True,
    server_api=ServerApi('1')
)
db = client["XP"]
collection = db["XP"]

load_dotenv(dotenv_path="env.env")
BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_TOKEN = os.environ["GEMINI_TOKEN"]

genai.configure(api_key=GEMINI_TOKEN)
model = genai.GenerativeModel("models/gemma-3n-e4b-it")

intents = discord.Intents.default()
intents.members = True

bot = discord.Bot(intents=intents)

colors = {
    "-": discord.Color.red(),
    "+": discord.Color.brand_green(),
    "=": discord.Color.blue()
}

ranks = {
    1352355657013133426: 250,
    1300986756396617728: 450,
    1352355717906038915: 600,
    1352355954305400915: 850
}

send_test_ranks = {
    1352355528428490834,
    1300986829138296842,
    1300986756396617728,
    1352357229663096903,
    1300986279659569235
}

JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DataBase", "logs_channel.json")

async def get_user_xp(user_id: int) -> int:
    try:
        result = await collection.find_one({"user_id": user_id})
        if result:
            return result["number"]
        return 0
    except Exception as e:
        print(f"Error getting user XP: {e}")
        return 0

async def set_user_xp(user_id: int, xp: int):
    try:
        await collection.update_one(
            {"user_id": user_id},
            {"$set": {"number": xp}},
            upsert=True
        )
    except Exception as e:
        print(f"Error setting user XP: {e}")

async def check_xp(member: discord.Member):
    try:
        user_xp = await get_user_xp(member.id)
        if user_xp == 0:
            return
        sorted_ranks = sorted(ranks.items(), key=lambda x: x[1])
        member_role_ids = {role.id for role in member.roles}
        current_role_index = None
        for i, (role_id, xp_needed) in enumerate(sorted_ranks):
            if role_id in member_role_ids:
                current_role_index = i
                break
        next_role_index = 0 if current_role_index is None else current_role_index + 1
        if next_role_index < len(sorted_ranks):
            next_role_id, next_role_xp = sorted_ranks[next_role_index]
            if user_xp >= next_role_xp:
                guild = member.guild
                next_role = guild.get_role(next_role_id)
                if next_role is None:
                    return
                old_roles = [guild.get_role(rid) for rid, _ in sorted_ranks if guild.get_role(rid) in member.roles]
                for old_role in old_roles:
                    if old_role:
                        await member.remove_roles(old_role)
                await member.add_roles(next_role)
                await set_user_xp(member.id, 0)
                try:
                    with open(JSON_PATH, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        promotion_channel_id = data.get("promotion_channel", -1)
                        promotion_channel = guild.get_channel(promotion_channel_id)
                        if promotion_channel:
                            await promotion_channel.send(embed=discord.Embed(
                                title="`Автоматическое повышение`",
                                description=f"`{member.mention} на ранг {next_role.mention} за {next_role_xp} ⚛︎ XP.`",
                                colour=0x48B5D6))
                except Exception:
                    pass
    except Exception as e:
        print(f"Error in check_xp: {e}")

async def send_log(ctx, message: str, type: str):
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
            channel_id = data.get("channel", -1)
            channel = bot.get_channel(channel_id)
            if channel:
                color = colors.get(type, discord.Color.red())
                await channel.send(embed=discord.Embed(title=message, color=color))
            else:
                await ctx.send(embed=discord.Embed(title="Ошибка", description="Не удалось найти канал с указанным ID.", color=discord.Color.red()), delete_after=5)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Файл логов не найден или содержит неверный формат.", color=discord.Color.red()), delete_after=5)

def has_allowed_role(ctx, slash_command_name: str = "") -> bool:
    role_ids = {role.id for role in ctx.author.roles}
    if role_ids & {1352360671198838824, 1300600118202077246, 1300601915263946814}:
        if slash_command_name in {"setxp", "setxpforgroup"} and 1352360671198838824 in role_ids:
            return False
        return True
    return False

def get_members_from_mentions(guild: discord.Guild, mentions: list[str]) -> list[discord.Member]:
    members = []
    for mention in mentions:
        if mention.startswith('<@') and mention.endswith('>'):
            user_id = int(mention.strip('<@!>'))
            member = guild.get_member(user_id)
            if member is not None:
                members.append(member)
    return members

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
        with open(JSON_PATH, "w", encoding="utf-8") as file:
            json.dump({"channel": -1, "promotion_channel": -1}, file, ensure_ascii=False, indent=4)

    try:
        for guild in bot.guilds:
            for member in guild.members:
                if not member.bot:
                    if await get_user_xp(member.id) == 0:
                        await set_user_xp(member.id, 0)
    except Exception as e:
        print(f"Error initializing users: {e}")

    try:
        for guild in bot.guilds:
            for member in guild.members:
                if not member.bot:
                    await check_xp(member)
    except Exception as e:
        print(f"Error checking XP: {e}")

    await asyncio.sleep(850)
    try:
        channel = bot.get_channel(1374363499458727946)
        if channel:
            await channel.send(embed=discord.Embed(
                title="Я погружаюсь в сон...",
                description=f"Но если ты решишь разбудить меня - перейди по этой ссылке: {url}",
                color=discord.Color.red()
            ))
    except Exception as e:
        print(f"Error sending sleep message: {e}")

@bot.event
async def on_member_join(member):
    try:
        if not member.bot:
            if await get_user_xp(member.id) == 0:
                await set_user_xp(member.id, 0)
            await check_xp(member)
    except Exception as e:
        print(f"Error in on_member_join: {e}")

@bot.event
async def on_member_update(before, after):
    try:
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        added_roles = after_roles - before_roles
        if added_roles:
            for role in added_roles:
                if role.id in send_test_ranks:
                    await after.send("""
> Вы готовы к переходу на следующий ранг. Необходимые каналы:
https://discord.com/channels/1300485165994217472/1300670260583862335
https://discord.com/channels/1300485165994217472/1301504588393877514
https://discord.com/channels/1300485165994217472/1350278142107062312
""")
    except Exception as e:
        print(f"Error in on_member_update: {e}")

@bot.slash_command(name="xp")
async def xp(ctx, member: discord.Member = None):
    try:
        if member is None:
            member = ctx.author
        xp_amount = await get_user_xp(member.id)
        await check_xp(member)
        await ctx.send(embed=discord.Embed(title="Баланс XP", description=f"{member.mention} имеет `{xp_amount} ⚛︎` XP.", colour=0x48B5D6))
    except Exception as e:
        print(f"Error in xp slash_command: {e}")
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Произошла ошибка при получении XP.", color=discord.Color.red()), delete_after=5)

@bot.slash_command(name="addxp")
async def addxp(ctx, amount: int, member: discord.Member):
    try:
        if not has_allowed_role(ctx):
            await ctx.send(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), delete_after=5)
            return
        current_xp = await get_user_xp(member.id)
        new_xp = current_xp + amount
        await set_user_xp(member.id, new_xp)
        await check_xp(member)
        await send_log(ctx, f"{ctx.author.mention} выдал {member.mention} {amount} баллов.", "+")
        await ctx.send(embed=discord.Embed(title="XP Добавлено", description=f"{member.mention} получил `{amount} ⚛︎` XP.\nНовый баланс: `{new_xp} ⚛︎`", colour=0x48B5D6))
    except Exception as e:
        print(f"Error in addxp slash_command: {e}")
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Произошла ошибка при добавлении XP.", color=discord.Color.red()), delete_after=5)

@bot.slash_command(name="remxp")
async def remxp(ctx, amount: int, member: discord.Member):
    try:
        if not has_allowed_role(ctx):
            await ctx.send(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), delete_after=5)
            return
        current_xp = await get_user_xp(member.id)
        new_xp = max(current_xp - amount, 0)
        await set_user_xp(member.id, new_xp)
        await check_xp(member)
        await send_log(ctx, f"{ctx.author.mention} снял {member.mention} {amount} баллов.", "-")
        await ctx.send(embed=discord.Embed(title="XP Удалено", description=f"{member.mention} потерял `{amount} ⚛︎` XP.\nНовый баланс: `{new_xp} ⚛︎`", colour=0x48B5D6))
    except Exception as e:
        print(f"Error in remxp slash_command: {e}")
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Произошла ошибка при удалении XP.", color=discord.Color.red()), delete_after=5)

@bot.slash_command(name="setxp")
async def setxp(ctx, amount: int, member: discord.Member):
    try:
        if not has_allowed_role(ctx, "setxp"):
            await ctx.send(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), delete_after=5)
            return
        amount_to_set = max(amount, 0)
        await set_user_xp(member.id, amount_to_set)
        await check_xp(member)
        await send_log(ctx, f"{ctx.author.mention} выставил {member.mention} {amount} баллов.", "=")
        await ctx.send(embed=discord.Embed(title="XP Установлено", description=f"Баланс {member.mention} установлен на `{amount_to_set} ⚛︎`", colour=0x48B5D6))
    except Exception as e:
        print(f"Error in setxp slash_command: {e}")
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Произошла ошибка при установке XP.", color=discord.Color.red()), delete_after=5)

@bot.slash_command(name="addxptogroup")
async def addxptogroup(ctx, amount: int, *, mentions: str):
    try:
        if not has_allowed_role(ctx):
            await ctx.send(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), delete_after=5)
            return
        mention_list = mentions.split()
        members = get_members_from_mentions(ctx.guild, mention_list)
        if not members:
            await ctx.send(embed=discord.Embed(title="Ошибка", description="Не удалось найти указанных участников.", colour=0x48B5D6))
            return
        for member in members:
            current_xp = await get_user_xp(member.id)
            new_xp = current_xp + amount
            await set_user_xp(member.id, new_xp)
            await check_xp(member)
        mentions_str = "\n".join(member.mention for member in members)
        await send_log(ctx, f"{ctx.author.mention} выдал {amount} баллов группе: {mentions_str}", "+")
        await ctx.send(embed=discord.Embed(title="XP Добавлено группе", description=f"Добавлено по `{amount} ⚛︎` следующим участникам:\n{mentions_str}", colour=0x48B5D6))
    except Exception as e:
        print(f"Error in addxptogroup slash_command: {e}")
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Произошла ошибка при добавлении XP группе.", color=discord.Color.red()), delete_after=5)

@bot.slash_command(name="remxpfromgroup")
async def remxpfromgroup(ctx, amount: int, *, mentions: str):
    try:
        if not has_allowed_role(ctx):
            await ctx.send(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), delete_after=5)
            return
        mention_list = mentions.split()
        members = get_members_from_mentions(ctx.guild, mention_list)
        if not members:
            await ctx.send(embed=discord.Embed(title="Ошибка", description="Не удалось найти указанных участников.", colour=0x48B5D6))
            return
        for member in members:
            current_xp = await get_user_xp(member.id)
            new_xp = max(current_xp - amount, 0)
            await set_user_xp(member.id, new_xp)
            await check_xp(member)
        mentions_str = "\n".join(member.mention for member in members)
        await send_log(ctx, f"{ctx.author.mention} снял {amount} баллов группе: {mentions_str}", "-")
        await ctx.send(embed=discord.Embed(title="XP Удалено у группы", description=f"Убрано по `{amount} ⚛︎` у следующих участников:\n{mentions_str}", colour=0x48B5D6))
    except Exception as e:
        print(f"Error in remxpfromgroup slash_command: {e}")
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Произошла ошибка при удалении XP у группы.", color=discord.Color.red()), delete_after=5)

@bot.slash_command(name="setxpforgroup")
async def setxpforgroup(ctx, amount: int, *, mentions: str):
    try:
        if not has_allowed_role(ctx, "setxpforgroup"):
            await ctx.send(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), delete_after=5)
            return
        mention_list = mentions.split()
        members = get_members_from_mentions(ctx.guild, mention_list)
        if not members:
            await ctx.send(embed=discord.Embed(title="Ошибка", description="Не удалось найти указанных участников.", colour=0x48B5D6))
            return
        amount_to_set = max(amount, 0)
        for member in members:
            await set_user_xp(member.id, amount_to_set)
            await check_xp(member)
        mentions_str = "\n".join(member.mention for member in members)
        await send_log(ctx, f"{ctx.author.mention} выставил {amount} баллов группе: {mentions_str}", "=")
        await ctx.send(embed=discord.Embed(title="XP Установлено группе", description=f"Баланс установлен на `{amount_to_set} ⚛︎` следующим участникам:\n{mentions_str}", colour=0x48B5D6))
    except Exception as e:
        print(f"Error in setxpforgroup slash_command: {e}")
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Произошла ошибка при установке XP группе.", color=discord.Color.red()), delete_after=5)

@bot.slash_command(name="about_bot")
async def about_bot(ctx):
    try:
        botik = ctx.bot.user
        embed = discord.Embed(title=f"Информация о боте {botik.name}", description="Привет! Я создан специально для сервера фракции Лазарет на Элитарпия РП", color=0x5865F2)
        embed.set_thumbnail(url=botik.display_avatar.url)
        try:
            if botik.banner:
                embed.set_image(url=botik.banner.url)
        except AttributeError:
            pass
        embed.add_field(name="Имя бота", value=botik.name, inline=True)
        embed.add_field(name="ID бота", value=str(botik.id), inline=True)
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error in about_bot slash_command: {e}")
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Произошла ошибка при получении информации о боте.", color=discord.Color.red()), delete_after=5)

@bot.slash_command(name="chchannel")
async def chchannel(ctx, channel: discord.TextChannel):
    try:
        role_ids = {role.id for role in ctx.author.roles}
        if role_ids & {1300600118202077246}:
            try:
                with open(JSON_PATH, "r", encoding="utf-8") as file:
                    data = json.load(file)
                data["channel"] = channel.id
                with open(JSON_PATH, "w", encoding="utf-8") as file:
                    json.dump(data, file, ensure_ascii=False, indent=4)
                await ctx.send(embed=discord.Embed(title=f"Канал для логов был изменен на {channel.mention}", colour=0x48B5D6))
            except Exception as e:
                await ctx.send(embed=discord.Embed(title="Ошибка", description=f"Ошибка при изменении канала: {e}", color=discord.Color.red()), delete_after=5)
        else:
            await ctx.send(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), delete_after=5)
    except Exception as e:
        print(f"Error in chchannel slash_command: {e}")

@bot.slash_command(name="chpromchannel")
async def chpromchannel(ctx, channel: discord.TextChannel):
    try:
        role_ids = {role.id for role in ctx.author.roles}
        if role_ids & {1300600118202077246}:
            try:
                with open(JSON_PATH, "r", encoding="utf-8") as file:
                    data = json.load(file)
                data["promotion_channel"] = channel.id
                with open(JSON_PATH, "w", encoding="utf-8") as file:
                    json.dump(data, file, ensure_ascii=False, indent=4)
                await ctx.send(embed=discord.Embed(title=f"Канал для логов повышений был изменен на {channel.mention}", colour=0x48B5D6))
            except Exception as e:
                await ctx.send(embed=discord.Embed(title="Ошибка", description=f"Ошибка при изменении канала: {e}", color=discord.Color.red()), delete_after=5)
        else:
            await ctx.send(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), delete_after=5)
    except Exception as e:
        print(f"Error in chpromchannel slash_command: {e}")

@bot.slash_command(name="ask")
async def ask(ctx, *, prompt: str):
    try:
        async with ctx.typing():
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    candidate_count=1,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=256
                )
            )
        await ctx.send(response.text[:2000])
    except Exception as e:
        print(f"Error in ask slash_command: {e}")
        await ctx.send(embed=discord.Embed(title="Ошибка", description="Произошла ошибка при обращении к AI.", color=discord.Color.red()), delete_after=5)

Thread(target=run_flask).start()
bot.run(BOT_TOKEN)