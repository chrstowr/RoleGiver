import os
import discord
import asyncio

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
# TODO: Add Option to make RAS with no roles

async def action_queue_clock():
    while True:
        if len(role_giver.action_queue) > 0:
            print(f'Q: {role_giver.action_queue}')
            await role_giver.action_queue_worker()
        await asyncio.sleep(.05)

@bot.event
async def on_ready():
    # Show connected guilds
    print(f'{bot.user.name} is connected to the following guilds:')
    guilds = bot.guilds
    for g in guilds:
        print(f'{g.name} | (id: {g.id})')
    print("Loading sessions from disk....")
    await role_giver.load_sessions_from_file()
    print(f'Number of sessions loaded: {role_giver.session_count()}')

    print(f'Starting RAS Queue worker')
    await bot.loop.create_task(action_queue_clock())


@bot.event
async def on_disconnect():
    print('Carry armor has disconnected from discord')


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


# Role giver clean command - Cleans up all active RAS sessions, make sure they have emotes and state of
# users who are supposed to have reactions do have them
@bot.command(name='clean', help='Runs a cleanup service that verifies all active RAS')
async def clean(ctx, *args):
    # Ideas:
    # All - Cleans all RASs on list (WARNING: This could be resource intensive if there are alot of users and RAS)
    # channel - cleans all RAS in a channel
    # id - pass id of a message
    pass


@bot.command(name='dumpsessions', help='')
async def dumpsessions(ctx, *args):
    data = role_giver.ras_sessions
    print(f'Overall: {data}')
    for i in data:
        i.print()


bot.run(TOKEN)
