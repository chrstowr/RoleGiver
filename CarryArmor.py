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

role_giver = RoleGiver(bot)


@bot.event
async def on_ready():
    # Show connected guilds
    print(f'{bot.user.name} is connected to the following guilds:')
    guilds = bot.guilds
    for g in guilds:
        print(f'{g.name} | (id: {g.id})')


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
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return

    # On reaction add listener for role giver
    if role_giver.check_for_ras(reaction.message) is True:
        await role_giver.add_role(reaction, user)


@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user:
        return

    # On reaction remove listener for role giver
    if role_giver.check_for_ras(reaction.message) is True:
        await role_giver.remove_role(reaction, user)


# Role giver create command - Calls new RG create form
@bot.command(name='create', help='Create a new RAS')
async def create(ctx, *args):
    # start routine to create role giving message
    # Check ADMIN rights?
    status = await role_giver.create(ctx)
    print(f'Status: {status}')


# Role giver clean command - Cleans up all active RAS sessions, make sure they have emotes and state of
# users who are supposed to have reactions do have them
@bot.command(name='clean', help='Runs a cleanup service that verifies all active RAS')
async def clean(ctx, *args):
    # Ideas:
    # All - Cleans all RASs on list (WARNING: This could be resource intensive if there are alot of users and RAS)
    # channel - cleans all RAS in a channel
    # id - pass id of a message
    pass


bot.run(TOKEN)
