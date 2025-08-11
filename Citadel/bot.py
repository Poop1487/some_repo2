import discord
from dotenv import load_dotenv
import os
import sqlite3
import json
import asyncio
import requests

url = "https://citadel-hnll.onrender.com"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "DataBase", "xp.db")
JSON_PATH = os.path.join(BASE_DIR, "DataBase", "logs_channel.json")

db = sqlite3.connect(DB_PATH)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, xp INTEGER NOT NULL)")
db.commit()

load_dotenv(dotenv_path="env.env")
# BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_TOKEN = os.environ["BOT_TOKEN"]

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

async def keep_alive():
    while True:
        try:
            requests.get(url=url)
        except Exception as error:
            bot.get_channel(1374363499458727946).send(f"<@926130802243305512> Далбаебище исправь меня, вот ошибка: {error}")
        await asyncio.sleep(930)
            
async def check_xp(member: discord.Member):
    cursor.execute("SELECT xp FROM users WHERE id = ?", (member.id,))
    result = cursor.fetchone()
    if not result:
        return
    user_xp = result[0]
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
            cursor.execute("UPDATE users SET xp = ? WHERE id = ?", (0, member.id))
            db.commit()
            try:
                with open(JSON_PATH, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    promotion_channel_id = data.get("promotion_channel", -1)
                    promotion_channel = guild.get_channel(promotion_channel_id)
                    if promotion_channel:
                        await promotion_channel.send(embed=discord.Embed(title="`Автоматическое повышение`", description=f"`{member.mention} на ранг {next_role.mention} за {next_role_xp} ⚛︎ XP.`", colour=0x48B5D6))
            except Exception:
                pass

async def send_log(ctx: discord.ApplicationContext, message: str, type: str):
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
            channel_id = data.get("channel", -1)
            channel = bot.get_channel(channel_id)
            if channel:
                color = colors.get(type, discord.Color.red())
                await channel.send(embed=discord.Embed(title=message, color=color))
            else:
                await ctx.respond(embed=discord.Embed(title="Ошибка", description="Не удалось найти канал с указанным ID.", color=discord.Color.red()), ephemeral=True)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="Файл логов не найден или содержит неверный формат.", color=discord.Color.red()), ephemeral=True)

def has_allowed_role(ctx: discord.ApplicationContext, command_name: str = "") -> bool:
    role_ids = {role.id for role in ctx.user.roles}
    if role_ids & {1352360671198838824, 1300600118202077246, 1300601915263946814}:
        if command_name in {"setxp", "setxpforgroup"} and 1352360671198838824 in role_ids:
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
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(JSON_PATH, "w", encoding="utf-8") as file:
            json.dump({"channel": -1, "promotion_channel": -1}, file, ensure_ascii=False, indent=4)
    for guild in bot.guilds:
        for member in guild.members:
            cursor.execute("SELECT xp FROM users WHERE id = ?", (member.id,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO users (id, xp) VALUES (?, ?)", (member.id, 0))
    db.commit()

    for guild in bot.guilds:
        for member in guild.members:
            await check_xp(member)
    
    await keep_alive()

@bot.event
async def on_member_join(member):
    cursor.execute("SELECT xp FROM users WHERE id = ?", (member.id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (id, xp) VALUES (?, ?)", (member.id, 0))
        db.commit()
    await check_xp(member)

@bot.event
async def on_member_update(before, after):
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
                
@bot.slash_command(name="xp", description="Review someone's XP")
async def xp(ctx: discord.ApplicationContext, member: discord.Member):
    cursor.execute('SELECT xp FROM users WHERE id = ?', (member.id,))
    result = cursor.fetchone()
    xp_amount = result[0] if result else 0
    await check_xp(member)
    await ctx.respond(embed=discord.Embed(title="Баланс XP", description=f"{member.mention} имеет `{xp_amount} ⚛︎` XP.", colour=0x48B5D6))

@bot.slash_command(name="addxp", description="Give XP to someone")
async def addxp(ctx: discord.ApplicationContext, amount: int, member: discord.Member):
    if not has_allowed_role(ctx):
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), ephemeral=True)
        return
    cursor.execute('SELECT xp FROM users WHERE id = ?', (member.id,))
    result = cursor.fetchone()
    newAm = (result[0] if result else 0) + amount
    cursor.execute('UPDATE users SET xp = ? WHERE id = ?', (newAm, member.id))
    db.commit()
    await check_xp(member)
    await send_log(ctx, f"{ctx.author.mention} выдал {member.mention} {amount} баллов.", "+")
    await ctx.respond(embed=discord.Embed(title="XP Добавлено", description=f"{member.mention} получил `{amount} ⚛︎` XP.\nНовый баланс: `{newAm} ⚛︎`", colour=0x48B5D6))

@bot.slash_command(name="remxp", description="Remove XP from someone")
async def remxp(ctx: discord.ApplicationContext, amount: int, member: discord.Member):
    if not has_allowed_role(ctx):
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), ephemeral=True)
        return
    cursor.execute('SELECT xp FROM users WHERE id = ?', (member.id,))
    result = cursor.fetchone()
    current_xp = result[0] if result else 0
    newAm = max(current_xp - amount, 0)
    cursor.execute('UPDATE users SET xp = ? WHERE id = ?', (newAm, member.id))
    db.commit()
    await check_xp(member)
    await send_log(ctx, f"{ctx.author.mention} снял {member.mention} {amount} баллов.", "-")
    await ctx.respond(embed=discord.Embed(title="XP Удалено", description=f"{member.mention} потерял `{amount} ⚛︎` XP.\nНовый баланс: `{newAm} ⚛︎`", colour=0x48B5D6))

@bot.slash_command(name="setxp", description="Set someone's XP to a certain value")
async def setxp(ctx: discord.ApplicationContext, amount: int, member: discord.Member):
    if not has_allowed_role(ctx, "setxp"):
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), ephemeral=True)
        return
    amount_to_set = max(amount, 0)
    cursor.execute("UPDATE users SET xp = ? WHERE id = ?", (amount_to_set, member.id))
    db.commit()
    await check_xp(member)
    await send_log(ctx, f"{ctx.author.mention} выставил {member.mention} {amount} баллов.", "=")
    await ctx.respond(embed=discord.Embed(title="XP Установлено", description=f"Баланс {member.mention} установлен на `{amount_to_set} ⚛︎`", colour=0x48B5D6))

@bot.slash_command(name="addxptogroup", description="Add XP to the members from the given group")
async def addexptogroup(ctx: discord.ApplicationContext, amount: int, mentions: str = discord.Option(description="Введите пинги участников через пробел", required=True)):
    if not has_allowed_role(ctx):
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), ephemeral=True)
        return
    mention_list = mentions.split()
    members = get_members_from_mentions(ctx.guild, mention_list)
    if not members:
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="Не удалось найти указанных участников.", colour=0x48B5D6))
        return
    for member in members:
        cursor.execute('SELECT xp FROM users WHERE id = ?', (member.id,))
        result = cursor.fetchone()
        newAm = (result[0] if result else 0) + amount
        cursor.execute('UPDATE users SET xp = ? WHERE id = ?', (newAm, member.id))
        await check_xp(member)
    db.commit()
    mentions_str = "\n".join(member.mention for member in members)
    await send_log(ctx, f"{ctx.author.mention} выдал {amount} баллов группе: {mentions_str}", "+")
    await ctx.respond(embed=discord.Embed(title="XP Добавлено группе", description=f"Добавлено по `{amount} ⚛︎` следующим участникам:\n{mentions_str}", colour=0x48B5D6))

@bot.slash_command(name="remxpfromgroup", description="Remove XP from members of the given group")
async def remexpfromgroup(ctx: discord.ApplicationContext, amount: int, mentions: str = discord.Option(description="Введите пинги участников через пробел", required=True)):
    if not has_allowed_role(ctx):
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), ephemeral=True)
        return
    mention_list = mentions.split()
    members = get_members_from_mentions(ctx.guild, mention_list)
    if not members:
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="Не удалось найти указанных участников.", colour=0x48B5D6))
        return
    for member in members:
        cursor.execute('SELECT xp FROM users WHERE id = ?', (member.id,))
        result = cursor.fetchone()
        current_xp = result[0] if result else 0
        newAm = max(current_xp - amount, 0)
        cursor.execute('UPDATE users SET xp = ? WHERE id = ?', (newAm, member.id))
        await check_xp(member)
    db.commit()
    mentions_str = "\n".join(member.mention for member in members)
    await send_log(ctx, f"{ctx.author.mention} снял {amount} баллов группе: {mentions_str}", "-")
    await ctx.respond(embed=discord.Embed(title="XP Удалено у группы", description=f"Убрано по `{amount} ⚛︎` у следующих участников:\n{mentions_str}", colour=0x48B5D6))

@bot.slash_command(name="setxpforgroup", description="Set XP of every member from the given group to the certain value")
async def setexpforgroup(ctx: discord.ApplicationContext, amount: int, mentions: str = discord.Option(description="Введите пинги участников через пробел", required=True)):
    if not has_allowed_role(ctx, "setxpforgroup"):
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), ephemeral=True)
        return
    mention_list = mentions.split()
    members = get_members_from_mentions(ctx.guild, mention_list)
    if not members:
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="Не удалось найти указанных участников.", colour=0x48B5D6))
        return
    amount_to_set = max(amount, 0)
    for member in members:
        cursor.execute('UPDATE users SET xp = ? WHERE id = ?', (amount_to_set, member.id))
        await check_xp(member)
    db.commit()
    mentions_str = "\n".join(member.mention for member in members)
    await send_log(ctx, f"{ctx.author.mention} выставил {amount} баллов группе: {mentions_str}", "=")
    await ctx.respond(embed=discord.Embed(title="XP Установлено группе", description=f"Баланс установлен на `{amount_to_set} ⚛︎` следующим участникам:\n{mentions_str}", colour=0x48B5D6))

@bot.slash_command(name="about_bot", description="Get info about bot")
async def about_bot(ctx: discord.ApplicationContext):
    botik = ctx.bot.user
    embed = discord.Embed(title=f"Информация о боте {botik.name}", description="Привет! Я создан специально для сервера фракции Лазарет на Элитарпия РП", color=0x5865F2)
    embed.set_thumbnail(url=botik.display_avatar.url)
    try:
        banner_url = botik.banner.url
        embed.set_image(url=banner_url)
    except AttributeError:
        pass
    embed.add_field(name="Имя бота", value=botik.name, inline=True)
    embed.add_field(name="ID бота", value=str(botik.id), inline=True)
    await ctx.respond(embed=embed)

@bot.slash_command(name="chchannel", description="Change logs sending channel (Access only head doctor)")
async def chchannel(ctx: discord.ApplicationContext, channel: discord.TextChannel):
    role_ids = {role.id for role in ctx.user.roles}
    if role_ids & {1300600118202077246}:
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        data["channel"] = channel.id
        with open(JSON_PATH, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        await ctx.respond(embed=discord.Embed(title=f"Канал для логов был изменен на {channel.mention}", colour=0x48B5D6))
    else:
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name="chpromchannel", description="Change logs sending channel (Access only head doctor)")
async def chpromchannel(ctx: discord.ApplicationContext, channel: discord.TextChannel):
    role_ids = {role.id for role in ctx.user.roles}
    if role_ids & {1300600118202077246}:
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        data["promotion_channel"] = channel.id
        with open(JSON_PATH, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        await ctx.respond(embed=discord.Embed(title=f"Канал для логов повышений был изменен на {channel.mention}", colour=0x48B5D6))
    else:
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name="принять", description="Join to the fraction")
async def принять(ctx: discord.ApplicationContext, member: discord.Member):
    if not has_allowed_role(ctx):
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="У вас нет прав на выполнение этой команды.", color=discord.Color.red()), ephemeral=True)
        return
    if ctx.channel_id == 1300669144856789023:
        await member.send("""
> Добро пожаловать в Лазарет! Ознакомьтесь с ключевыми каналами:
https://discord.com/channels/1300485165994217472/1300668883266703360
https://discord.com/channels/1300485165994217472/1300669020642742282
https://discord.com/channels/1300485165994217472/1300669769514614914
https://discord.com/channels/1300485165994217472/1349466548619710515
https://discord.com/channels/1300485165994217472/1395854017439072306
https://discord.com/channels/1300485165994217472/1300670260583862335
""")
        guild = member.guild
        await member.remove_roles(guild.get_role(1300986977017135147))
        for id in {1352359283689525390, 1352359186524143778, 1352355528428490834, 1352359414329512037, 1352359802294243421}:
            role = guild.get_role(id)
            await member.add_roles(role)
        await ctx.respond(embed=discord.Embed(title="Принятие успешно", description=f"{member.mention} был принят в лазарет", colour=0x48B5D6))
    else:
        await ctx.respond(embed=discord.Embed(title="Ошибка", description="Эта команда не предназначена для этого канала.", color=discord.Color.red()), ephemeral=True)

bot.run(BOT_TOKEN)