import os
import asyncio
import discord

from datetime import datetime
from dotenv import load_dotenv
from discord.ext import commands
from RoleGiver.RoleGiver import RoleGiver

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set prefix for bot
bot = commands.Bot(command_prefix='c!')
# Role giver object
role_giver = RoleGiver(bot)


# TODO: Add backup system for JSON file

async def action_queue_clock():
    while True:
        if len(role_giver.action_queue) > 0:
            await role_giver.action_queue_worker()
            await asyncio.sleep(.25)
        else:
            await asyncio.sleep(1)


@bot.event
async def on_ready():
    # Show connected guilds
    print(f'{bot.user.name} is connected to the following guilds:')
    guilds = bot.guilds
    for g in guilds:
        print(f'{g.name} | (id: {g.id})')
    print()

    print("Loading sessions from disk....")
    await role_giver.load_sessions_from_file()

    session_count = role_giver.session_count()
    print(f'Number of sessions loaded: {session_count}\n')

    if session_count > 0:
        print('Validating RAS session states...')
        await role_giver.validate_state()
    print()

    print(f'Starting RAS Queue worker...')
    await bot.loop.create_task(action_queue_clock())
    print(f'Ready to go!')


@bot.event
async def on_disconnect():
    datetime_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'Carry armor has disconnected from discord - {datetime_now}')


@bot.event
async def on_connect():
    datetime_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'Carry armor has connected with discord - {datetime_now}')


@bot.event
async def on_message(message):
    # Check to avoid bot responding to itself
    if message.author == bot.user:
        return

    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    # On reaction add listener for role giver
    if role_giver.check_if_ras(payload.message_id) is True:
        await role_giver.on_reaction_listener(payload)


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return

    # On reaction remove listener for role giver
    if role_giver.check_if_ras(payload.message_id) is True:
        await role_giver.on_reaction_listener(payload)


# Role giver create command - Calls new RG create form
@bot.command(name='create', help='Create a new RAS')
async def create(ctx, *args):
    # start routine to create role giving message
    # Check ADMIN rights?
    status = await role_giver.create(ctx)
    print(f'Status of Create RAS session: {status}')


# Role giver edit command - Calls RG edit form
@bot.command(name='edit', help='Edit existing ras session')
async def edit(ctx, *args):
    # start routine to edit ras session
    # Check ADMIN rights?

    # Check if arg passed is valid msg id
    # Check if user calling edit is calling id in current guild
    if len(args) == 1:
        matching_ras = discord.utils.find(lambda m: str(m.message.id) == args[0]
                                                    and ctx.guild.id == m.guild.id, role_giver.ras_sessions)
        if matching_ras is not None:
            status = await role_giver.edit(ctx, matching_ras)
            print(f'Status of edit RAS session: {status}')
        elif role_giver.word_check(args[0], 'help'):
            description = 'Description:\nEdit an existing RAS\'s channel, title/description, emotes/roles, unique state' \
                          ', or colour.\n\n'
            proper_format = 'Proper format:\nc!edit <message_id>\n\n'
            example = 'Example:\nc!edit 111111111111111111'
            await ctx.send(f'```{description}{proper_format}{example}```')


# Role giver edit command - Calls RG edit form
@bot.command(name='delete', help='Delete an RAS')
async def delete(ctx, *args):
    if len(args) == 1:
        matching_ras = discord.utils.find(lambda m: str(m.message.id) == args[0]
                                                    and ctx.guild.id == m.guild.id, role_giver.ras_sessions)
        if matching_ras is not None:
            status = await role_giver.delete(ctx, matching_ras)
            print(f'Status of delete RAS session: {status}')

@bot.command(name='dumpsessions', help='')
async def dumpsessions(ctx, *args):
    data = role_giver.ras_sessions
    print(f'Overall: {data}')
    for i in data:
        i.print()


@bot.command(name='ping', help='')
async def ping(ctx, *args):
    await ctx.send(f'Latency: {bot.latency * 1000:0.1f}ms')


bot.run(TOKEN)
