import os
import asyncio
import discord
import json
import random
import string

from time import perf_counter
from collections import deque
from json import JSONDecodeError
from pathlib import Path
from RoleGiver.Models.RASModels import RoleGiverSession, QueueItem
from RoleGiver.Models.StatusEnum import Status
from RoleGiver.Services.CreateFormServices import CreateForm
from RoleGiver.Services.EditFormServices import EditForm


class RoleGiver:

    def __init__(self, bot):
        self.bot = bot
        self.timeout = 320.00

        # Holds currently active RAS sessions
        self.ras_sessions = list()

        # Holds queue action items to execute role adds or removals
        self.action_queue = deque()

        self.queue_count = 0
        self.queue_time_sum = 0.0

    """#################################################
    create() - Routine that contains logic for the RAS (Reaction-based role Assignment System) create form.
    Helper function specific to create() will be defined under this function
    #################################################"""

    async def create(self, ctx):
        # Intialize create form object with context, bot handle, and ras_session reference
        createform = CreateForm(ctx, self.bot, self.ras_sessions)
        # Add steps
        createform.add_step(createform.get_channel)
        createform.add_step(createform.get_title_desc)
        createform.add_step(createform.get_emote_role)
        createform.add_step(createform.get_unique_flag)
        createform.add_step(createform.get_color)
        createform.add_step(createform.publish)
        # Run form
        form_result = await createform.run()
        # Handle result
        if form_result is Status.SUCCESS:
            self.save_sessions_to_file()
            return Status.SUCCESS
        else:
            return form_result

    """#################################################
       edit() - Routine that contains logic for the RAS (Reaction-based role Assignment System) edit form.
       Helper function specific to edit() will be defined under this function
    #################################################"""

    async def edit(self, ctx, ras_to_edit):
        editform = EditForm(self.bot, ctx, ras_to_edit)

        editform.add_step(editform.get_channel, "Posted Channel")
        editform.add_step(editform.get_title_desc, "Title/Description")
        editform.add_step(editform.get_emote_role, "Emotes/Roles")
        editform.add_step(editform.get_unique_flag, "Unique")
        editform.add_step(editform.get_color, "Colour")

        form_result = await editform.run()

        if form_result is Status.SUCCESS:
            self.save_sessions_to_file()
            await self.validate_state('message', [ras_to_edit.message.id])
            return Status.SUCCESS
        else:
            return form_result

    """#################################################
        delete() - Routine that contains logic for the RAS (Reaction-based role Assignment System) delete form.
        Helper function specific to delete() will be defined under this function
    #################################################"""

    async def delete(self, ctx, ras_to_delete):

        # Used as validation for delete
        validation_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))

        # Make EDIT_RAS message embed, add needed fields
        delete_window = None
        delete_embed = discord.Embed()
        delete_embed.colour = discord.Colour.blue()
        delete_embed.title = 'Delete RAS'  # Never changes, title of message
        delete_embed.description = f'Hello, {ctx.message.author.name}! To delete this RAS enter the validation string' \
                                   f' below, or type `cancel` to cancel this operation.'  # Message block used by bot
        delete_embed.add_field(name='Validation string:', value=f'`{validation_string}`', inline=False)
        delete_embed.add_field(name='tip:', value='Type `cancel` to stop',
                               inline=False)  # tips

        # Send update to edit window
        delete_window = await ctx.send(embed=delete_embed)

        # Send update to preview window
        preview_window = await ctx.send('Preview:\n', embed=ras_to_delete.message.embeds[0])
        print(ras_to_delete.message)
        # Add reacts to preview
        for reaction in ras_to_delete.message.reactions:
            await preview_window.add_reaction(reaction.emoji)

        def message_check(message):
            is_author = message.author == ctx.message.author
            in_correct_channel = message.channel == ctx.message.channel
            return is_author and in_correct_channel

        try:
            while True:
                response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)

                if self.word_check(response.content, 'cancel'):
                    await self.cancel_embed(delete_embed, delete_window, preview_window,
                                            title='Delete RAS :warning:',
                                            text='This delete RAS session was cancelled, use the delete command'
                                                 ' again to start another session.')
                    return Status.CANCEL
                elif self.word_check(response.content, validation_string):
                    # Save message id for validation
                    channel_name = ras_to_delete.message.channel.name
                    try:

                        # Clear all roles
                        for reaction in ras_to_delete.message.reactions:
                            role = ras_to_delete.find_role(reaction.emoji)
                            guild_role = discord.utils.find(lambda r: r == role,
                                                            ras_to_delete.guild.roles)
                            if guild_role is not None:
                                for member in guild_role.members:
                                    await member.remove_roles(role)

                        # Delete message
                        await ras_to_delete.message.delete()
                        # Delete from RAS session list
                        self.ras_sessions.remove(ras_to_delete)
                        # Save to disk
                        self.save_sessions_to_file()

                        # Delete preview window
                        await preview_window.delete()

                        # Update create RAS form with confirmation
                        delete_embed.title = 'Delete RAS  -  :white_check_mark:'
                        delete_embed.description = f'CONFIRMATION - The RAS posted in ' \
                                                   f'#{channel_name} has been deleted.'
                        delete_embed.colour = discord.Colour.green()
                        delete_embed.clear_fields()
                        await delete_window.edit(embed=delete_embed)

                        return Status.SUCCESS
                    except discord.Forbidden:
                        # Delete preview window
                        await preview_window.delete()
                        # Update create RAS form with confirmation
                        delete_embed.title = 'Delete RAS  -  :octagonal_sign:'
                        delete_embed.description = f'PERMISSION ERROR - The RAS posted in ' \
                                                   f'#{channel_name} was not deleted due to not having sufficient' \
                                                   f' permissions.'
                        delete_embed.colour = discord.Colour.red()
                        delete_embed.clear_fields()
                        await delete_window.edit(embed=delete_embed)
                        return Status.FAILURE
                    except discord.NotFound:
                        # Delete preview window
                        await preview_window.delete()
                        # Update create RAS form with confirmation
                        delete_embed.title = 'Delete RAS  -  :octagonal_sign:'
                        delete_embed.description = f'NOT FOUND ERROR - The RAS posted in ' \
                                                   f'#{channel_name} was not deleted because it was not found.'

                        delete_embed.clear_fields()
                        delete_embed.colour = discord.Colour.red()
                        await delete_window.edit(embed=delete_embed)
                        return Status.FAILURE
                    except discord.HTTPException:
                        # Delete preview window
                        await preview_window.delete()
                        # Update create RAS form with confirmation
                        delete_embed.title = 'Delete RAS  -  :octagonal_sign:'
                        delete_embed.description = f'DELETE FAILED - The RAS posted in ' \
                                                   f'#{channel_name} was not deleted.'
                        delete_embed.colour = discord.Colour.red()
                        delete_embed.clear_fields()
                        await delete_window.edit(embed=delete_embed)
                        return Status.FAILURE
                    except discord.DiscordException:
                        # Delete preview window
                        await preview_window.delete()
                        # Update create RAS form with confirmation
                        delete_embed.title = 'Delete RAS  -  :octagonal_sign:'
                        delete_embed.description = f'UNKNOWN ERROR - An unknown error has occurred which prevents' \
                                                   f' the deletion of the RAS in {channel_name}.'
                        delete_embed.colour = discord.Colour.red()
                        delete_embed.clear_fields()
                        await delete_window.edit(embed=delete_embed)
                        return Status.FAILURE
        except asyncio.TimeoutError:

            await self.timeout_embed(delete_embed, delete_window, preview_window,
                                     title='Delete RAS :octagonal_sign:',
                                     text='This delete RAS session has timed out, please use the '
                                          'previous command '
                                          'to try again.')
            return Status.TIMEOUT

    """#################################################
    Validating RAS states - Used to validate the RAS session state
    parameter: scope - used to set scope of search
        all - verify all RAS sessions in DB
        guild - Verify guild sessions
        channel - etc
        message - etc 
    #################################################"""

    async def validate_state(self, scope='all', id_list=None):
        ras_sessions_to_scan = None
        if scope == 'all':
            ras_sessions_to_scan = self.ras_sessions
        elif scope == 'message':
            ras_sessions_to_scan = list()
            for message_id in id_list:
                match = discord.utils.find(lambda r: r.message.id is message_id, self.ras_sessions)
                if match is not None:
                    ras_sessions_to_scan.append(match)
        elif scope == 'channel':
            pass
        elif scope == 'guild':
            pass

        # Ensure RAS message cache matches server's current state
        for ras in ras_sessions_to_scan:
            ras.message = await self.bot.get_channel(ras.channel.id).fetch_message(ras.message.id)

        ras_count = len(ras_sessions_to_scan)
        progress_tracker = 0
        # Interate thru messages and validate states, make case for unique and non-unique ras
        for ras in ras_sessions_to_scan:
            # TODO: Implement unique RAS validation
            # Due to reactions.users() being data heavy, download all to memory once into lists
            if ras.unique is True:
                ras_roles = ras.role_list()
                # make list of users in all reactions
                user_list = list()
                # make list of users = to the amount of reactions they have, seperate lists by reaction
                reaction_list = list()
                # iterate once through each reaction
                for reaction in ras.message.reactions:
                    users = await reaction.users().flatten()
                    reaction_list.append([reaction.emoji, users])
                    for user in users:
                        if user not in user_list and user != self.bot.user:
                            user_list.append(user)

                # Add users who have not reacted, but have roles associated with the RAS
                for ras_role in ras_roles:
                    for user in ras.message.guild.members:
                        if ras_role in user.roles and user != self.bot.user:
                            user_list.append(user)

                # iterate through user_list and validate against certain conditions
                for user in user_list:
                    # ignore bot

                    reactions_user_is_present_in = list()
                    for reaction in reaction_list:
                        if user in reaction[1]:
                            reactions_user_is_present_in.append(reaction[0])
                    # If 0 make sure user doesnt any of the roles
                    if len(reactions_user_is_present_in) < 1:
                        for ras_role in ras_roles:
                            if ras_role in user.roles:
                                ras.remove_user_from_cache_with_role(user, ras_role)
                                await user.remove_roles(ras_role)
                    # if 1, make sure user only has that one role
                    elif len(reactions_user_is_present_in) == 1:
                        # Role being requested thru the reaction
                        requested_role = ras.find_role(reactions_user_is_present_in[0])
                        # Compile list of roles that need to be removed
                        roles_to_remove = list()
                        for role in ras_roles:
                            if role in user.roles and role is not requested_role:
                                roles_to_remove.append(role)

                        # Make sure user has the role
                        if requested_role not in user.roles and requested_role is not None:
                            ras.cache_user_with_role(user, requested_role)
                            await user.add_roles(requested_role)

                        for role in roles_to_remove:
                            ras.remove_user_from_cache_with_role(user, role)
                            await user.remove_roles(role)
                    # Remove all roles and reactions
                    elif len(reactions_user_is_present_in) > 1:
                        # Remove all reactions user is present in
                        for reaction in reactions_user_is_present_in:
                            await ras.message.remove_reaction(reaction, user)
                        # Remove all roles
                        roles_to_remove = list()
                        for role in ras_roles:
                            if role in user.roles:
                                roles_to_remove.append(role)
                        for role in roles_to_remove:
                            ras.remove_user_from_cache_with_role(user, role)
                            await user.remove_roles(role)
            elif ras.unique is False:
                # iterate through each reaction ensure each user has matching role of that reaction
                for reaction in ras.message.reactions:
                    # List of users who used this reaction
                    users = await reaction.users().flatten()
                    # Role associated with reaction
                    role = ras.find_role(reaction.emoji)
                    if role is not None:
                        # Get users in guild who currently have the role
                        members_with_role = [u for u in ras.message.guild.members if role in u.roles]
                        # Validate each user on user list has role
                        for user in users:
                            # Cross check if user has role
                            result = discord.utils.find(lambda m: user == m, members_with_role)
                            if result is None and user != self.bot.user and role is not None:
                                ras.cache_user_with_role(user, role)
                                await user.add_roles(role)
                            elif result is not None and user != self.bot.user:
                                members_with_role.remove(user)

                        # The remaining members on members_with_role will have role removed
                        for member in members_with_role:
                            if member != self.bot:
                                ras.remove_user_from_cache_with_role(member, role)
                                await member.remove_roles(role)

            progress_tracker = progress_tracker + 1
            print(f'Progress: ({progress_tracker}/{ras_count})...')

    """#################################################
    Action functions - Handles all logic related to the action queue
    #################################################"""

    async def on_reaction_listener(self, payload):
        ras = discord.utils.find(lambda r: r.message.id == payload.message_id, self.ras_sessions)
        requested_role = ras.find_role(payload.emoji)

        check_if_reaction_exists = discord.utils.find(lambda r: r['emote'] == payload.emoji.name, ras.options)

        user = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
        if check_if_reaction_exists is not None:
            role_is_null_ras_is_unique = requested_role is None and ras.unique is True
            role_is_not_null = requested_role is not None
            if role_is_null_ras_is_unique is True or role_is_not_null:
                message_path = {'guild_id': payload.guild_id, 'channel_id': payload.channel_id,
                                'message_id': payload.message_id}
                emote = payload.emoji
                action = payload.event_type
                new_queue_item = QueueItem(user, message_path, ras, emote, action)
                self.action_queue.append(new_queue_item)
        else:
            await ras.message.remove_reaction(payload.emoji, user)

    async def action_queue_worker(self):
        t1 = perf_counter()
        action = self.action_queue.popleft()
        requested_role = action.ras.find_role(action.emote)
        if action.type == 'REACTION_ADD':
            if action.ras.unique is True:
                # TODO: Optimize unique RAS for speed, find out if there is faster method to send requests to discord
                #   i.e: add_reaction(), remove_reaction(), add_role(), remove_role()
                # Optimization list:
                # -Instead of reading reaction user lists from discord server, I am caching the user list locally.
                #   response time from module 3 reduced from 1500ms-600ms to < 1ms
                # 1: Get current state of message
                message = action.ras.message
                # 2: Get list of roles associate with RAS
                ras_roles = action.ras.role_list()
                # 3: Get reactions user has activated
                reaction_list = list()
                for reaction in action.ras.options:
                    # Check if user is in reaction.user list
                    users = reaction['users']
                    if action.user in users:
                        reaction_list.append(reaction)
                # 4: Compile list of roles that need to be removed
                t4 = perf_counter()
                for role in ras_roles:
                    if role is not None and role is not requested_role and role in action.user.roles:
                        action.ras.release_from_cache(action.user, role, action.emote.name)
                        await action.user.remove_roles(role)
                t5 = perf_counter()
                # print(f'Checking roles: {(t5-t4)*1000:0.2f}')
                # 5: Iterate thru list of reactions that need to be removed
                t6 = perf_counter()
                for reaction in reaction_list:
                    if reaction['emote'] != action.emote.name:
                        action.ras.release_from_cache(action.user, requested_role, reaction['emote'])
                        await message.remove_reaction(reaction['emote'], action.user)
                t7 = perf_counter()
                # print(f'Removing reactions: {(t7-t6)*1000:0.2f}')
                # 6: Make sure user has the role
                if requested_role not in action.user.roles:
                    await action.ras.cache_user(action.user, requested_role, action.emote)
                    if requested_role is not None:
                        await action.user.add_roles(requested_role)

                t2 = perf_counter()
                self.queue_count = self.queue_count + 1
                self.queue_time_sum = self.queue_time_sum + ((t2 - t1) * 1000)
                print(
                    f'{action.user}({action.type}) -- Avg queue action throughput time({self.queue_count}): '
                    f'{self.queue_time_sum / self.queue_count:0.2f} | Unique::ADD action time: {(t2 - t1) * 1000:0.2f}')
                return

            elif action.ras.unique is False and requested_role is not None:
                await action.user.add_roles(requested_role)
                t2 = perf_counter()
                self.queue_count = self.queue_count + 1
                self.queue_time_sum = self.queue_time_sum + ((t2 - t1) * 1000)
                print(
                    f'{action.user}({action.type}) -- Avg queue action throughput time({self.queue_count}):'
                    f' {self.queue_time_sum / self.queue_count:0.2f} | Not Unique::ADD action time: {(t2 - t1) * 1000:0.2f}')
                return
        elif action.type == 'REACTION_REMOVE' and requested_role in action.user.roles:
            await action.user.remove_roles(requested_role)
            t2 = perf_counter()
            self.queue_count = self.queue_count + 1
            self.queue_time_sum = self.queue_time_sum + ((t2 - t1) * 1000)
            print(
                f'{action.user}({action.type}) -- Avg queue action throughput time({self.queue_count}):'
                f' {self.queue_time_sum / self.queue_count:0.2f} | REMOVE action time: {(t2 - t1) * 1000:0.2f}')
            return

    #############################
    # Action helper functions   #
    #############################
    def check_if_ras(self, message_id):
        result = [m for m in self.ras_sessions if message_id == m.message.id]
        if len(result) > 0:
            return True
        else:
            return False

    """"################################################
    Save/Load functions for RAS session data
    ################################################"""

    def save_sessions_to_file(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data.json')
            session_data_file = Path(file)
            with open(session_data_file, 'w') as f:
                f.write(json.dumps(self.ras_sessions, indent=4, default=self.json_serialize_filter))
                f.close()
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')

    async def load_sessions_from_file(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                self.ras_sessions = await self.convert_to_ras_session_format(data)
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')

    # Helper - Take objects that are unserializable and format to serializable object
    @staticmethod
    def json_serialize_filter(obj):
        if isinstance(obj, RoleGiverSession):
            # clear user list before saving
            for op in obj.options:
                op['users'].clear()
            return {'msg': obj.message.id, 'channel': obj.channel.id, 'guild': obj.guild.id, 'unique': obj.unique,
                    'options': obj.options}
        elif isinstance(obj, discord.role.Role):
            return obj.id
        else:
            raise TypeError("Type %s not serializable" % type(obj))

    # Helper - converts the data received from JSON data file into the proper ras_session format
    async def convert_to_ras_session_format(self, data):
        ras_session_format = list()
        for item in data:
            session_item = RoleGiverSession()
            await session_item.convert_from_json(item, self.bot)
            ras_session_format.append(session_item)

        return ras_session_format

    """################################################
    Helper functions for both edit and create functions
    ################################################"""

    @staticmethod
    def verify_title_desc(message):
        if '|' in message:
            args = message.split('|')
            # Make sure only 2 fields were passed
            if len(args) > 2:
                return False
            else:
                # Strip leading and ending whitespaces
                for item in args:
                    item.strip()

                # Check if any fields are empty
                for item in args:
                    if len(item) < 1:
                        return False

                return True
        else:
            return False

    @staticmethod
    def word_check(message, word):
        if message.lower().strip().startswith(word):
            return True
        else:
            return False

    @staticmethod
    async def cancel_embed(embed: discord.Embed, create_ras_window: discord.Message, preview_ctx: discord.Message,
                           title='Cancelled :warning:',
                           text='This RAS form was cancelled. Your work was **not** saved.'):
        # Template for cancel embed
        embed.colour = discord.Colour.gold()
        embed.clear_fields()
        embed.title = title
        embed.description = text

        # if a preview window exists close it
        if preview_ctx is not None:
            await preview_ctx.delete()

        # Replace create window with cancel embed
        await create_ras_window.edit(embed=embed)

    @staticmethod
    async def timeout_embed(embed: discord.Embed, create_ras_window: discord.Message, preview_ctx: discord.Message,
                            title='Timeout :octagonal_sign:',
                            text='This RAS form has timed out. Use the previous command to try again'):
        # Template for timeout embed
        embed.colour = discord.Colour.red()
        embed.clear_fields()
        embed.title = title
        embed.description = text

        # if a preview window exists close it
        if preview_ctx is not None:
            await preview_ctx.delete()

        # Replace create window with timeout embed
        await create_ras_window.edit(embed=embed)

    def session_count(self):
        return len(self.ras_sessions)

    @staticmethod
    def is_int(value):
        try:
            int(value)
            return True
        except:
            return False

    def color_atlas(self, requested_color):
        exploded_color_str = requested_color.content.split(',')

        # Make sure three characters were passed
        if len(exploded_color_str) == 3:
            # Make sure all three are ints, and they are between 0 and 255
            for item in exploded_color_str:
                if self.is_int(item) is False:
                    return None
                else:
                    if 0 > int(item) > 255:
                        return None
            r = int(exploded_color_str[0])
            g = int(exploded_color_str[1])
            b = int(exploded_color_str[2])
            return discord.Colour.from_rgb(r, g, b)
        else:
            return None
