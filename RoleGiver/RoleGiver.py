import os
import asyncio
import discord
import json
import copy
import random
import string

from time import perf_counter
from collections import deque
from json import JSONDecodeError
from pathlib import Path
from RoleGiver.Models.RASModels import RoleGiverSession, QueueItem
from RoleGiver.Services.CreateFormServices import CreateForm


class RoleGiver:

    def __init__(self, bot):
        self.bot = bot
        self.SUCCESS = 0
        self.FAILURE = 1
        self.CANCEL = 2
        self.TIMEOUT = 4
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
    # async def create(self, ctx):
    #     # Timeout for each step
    #
    #     # Initialize needed variables
    #     ras_preview_window = None
    #     new_ras_session = RoleGiverSession()
    #     new_ras_session_embed = discord.Embed()
    #     new_ras_session_embed.colour = discord.Colour.default()
    #
    #     # Make CREATE_RAS message embed, add needed fields
    #     create_ras_window = None
    #     create_embed = discord.Embed()
    #     create_embed.colour = discord.Colour.blue()
    #     create_embed.title = 'Create RAS'  # Never changes, title of message
    #     create_embed.description = 'N/A'  # Message block used by bot
    #     create_embed.add_field(name='tip:', value='Type `cancel` at anytime to stop', inline=False)  # tips
    #
    #     # Steps in order to create new RAS message:
    #     """###################################
    #     # Ask for channel/guild
    #     ###################################"""
    #     """
    #     para: create_ras_window, create_embed, ras_preview_window, new_ras_session, new_ras_session_embed, timeout=320
    #     """
    #     create_embed.title = 'Create RAS - Step 1/?'
    #     create_embed.description = f'Hello, {ctx.message.author.name}! Please enter the channel you would like to' \
    #                                f' create an RAS in.'
    #     create_embed.insert_field_at(0, name='Example:', value='`#example_channel`', inline=False)
    #     create_ras_window = await ctx.send(embed=create_embed)
    #     ras_preview_window = await ctx.send('Preview:\n', embed=new_ras_session_embed)
    #
    #     # Wait for response from author
    #     # message_check() used to check if author responded in correct channel
    #     def message_check(message):
    #         is_author = message.author == ctx.message.author
    #         in_correct_channel = message.channel == ctx.message.channel
    #         return is_author and in_correct_channel
    #
    #     try:
    #         retry = True
    #         while retry is True:
    #             response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)
    #             if self.word_check(response.content, 'cancel'):
    #                 await self.cancel_embed(create_embed, create_ras_window, ras_preview_window,
    #                                         title='Create RAS :warning:',
    #                                         text='This create RAS sessions was cancelled, use the create command'
    #                                              ' again to start another session.')
    #                 return self.CANCEL
    #             elif len(response.channel_mentions) > 0:
    #                 if response.channel_mentions[0] in ctx.message.guild.channels:
    #                     channel = self.bot.get_channel(response.channel_mentions[0].id)
    #                     if channel is not None:
    #                         new_ras_session.channel = channel
    #                         new_ras_session.guild = channel.guild
    #                         retry = False
    #                     else:
    #                         await ctx.send('Unable to verify channel')
    #             else:
    #                 await ctx.send('Unable to verify channel')
    #
    #     except asyncio.TimeoutError:
    #
    #         await self.timeout_embed(create_embed, create_ras_window, ras_preview_window,
    #                                  title='Create RAS :octagonal_sign:',
    #                                  text='This Create RAS session has timed out, please use the \'c!create\' command '
    #                                       'again ')
    #         return self.TIMEOUT
    #
    #     """###################################
    #     # Ask for title and description
    #     ###################################"""
    #
    #     # Change create RAS window
    #
    #     create_embed.title = 'Create RAS - Step 2/?'
    #     create_embed.description = f'{ctx.message.author.name}, please type out the titles and description using ' \
    #                                f'this format: [title]|[description] '
    #     create_embed.set_field_at(0, name='Example:', value='`Test Title|This is a test description for a new RAS.`',
    #                               inline=False)
    #     await create_ras_window.edit(embed=create_embed)
    #
    #     # Wait for response from author
    #     # see message_check() in step 2
    #     try:
    #         retry = True
    #         while retry is True:
    #             response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)
    #             if self.word_check(response.content, 'cancel'):
    #                 await self.cancel_embed(create_embed, create_ras_window, ras_preview_window,
    #                                         title='Create RAS :warning:',
    #                                         text='This create RAS sessions was cancelled, use the create command'
    #                                              ' again to start another session.')
    #                 return self.CANCEL
    #             elif self.verify_title_desc(response.content):
    #                 retry = False
    #                 items = response.content.split('|')
    #                 new_ras_session_embed.title = items[0].strip()
    #                 new_ras_session_embed.description = items[1].strip()
    #                 await ras_preview_window.edit(embed=new_ras_session_embed)
    #             else:
    #                 await ctx.send('Invalid format detected, please look at example above.')
    #
    #     except asyncio.TimeoutError:
    #         await self.timeout_embed(create_embed, create_ras_window, ras_preview_window,
    #                                  title='Create RAS :octagonal_sign:',
    #                                  text='This Create RAS session has timed out, please use the \'c!create\' command '
    #                                       'again ')
    #         return self.TIMEOUT
    #
    #     """###################################
    #      # Ask for for emote and matching role
    #     ###################################"""
    #     # Change create RAS window
    #     create_embed.title = 'Create RAS - Step 3/?'
    #     create_embed.description = f'{ctx.message.author.name}, please list out the reaction/roles you would like to ' \
    #                                f'add: \n[:the_emote:]\' \'[@role]. To delete a line type \'del [int]\''
    #     create_embed.set_field_at(0, name='Example:', value='`:warning: @spoiler_squad`\n`del 1`',
    #                               inline=False)
    #     create_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop, `done` when you are done',
    #                               inline=False)
    #     new_ras_session_embed.add_field(name='Current options:', value='None', inline=False)
    #     await create_ras_window.edit(embed=create_embed)
    #
    #     # Wait for response from author
    #     # see message_check() in step 2
    #     try:
    #         retry = True
    #         options_strings = ['(This will not display on final published RAS)\n']
    #         while retry is True:
    #             response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)
    #             if self.word_check(response.content, 'cancel'):  # Check for 'cancel'
    #                 await self.cancel_embed(create_embed, create_ras_window, ras_preview_window,
    #                                         title='Create RAS :warning:',
    #                                         text='This create RAS sessions was cancelled, use the create command'
    #                                              ' again to start another session.')
    #                 return self.CANCEL
    #             elif self.word_check(response.content, 'del'):
    #                 # Get first argument after delete
    #                 arg = response.content.strip(' ').split(' ')
    #                 if len(arg) > 1:
    #                     arg = arg[1].strip(' ')
    #                     # Check if is int
    #                     if self.is_int(arg) is True:
    #                         delete_option = int(arg)
    #                         if 0 < delete_option < len(options_strings):
    #                             # Remove from option list
    #                             option_to_remove = options_strings.pop(delete_option)
    #                             # Remove from RAS
    #                             await new_ras_session.remove_option(option_to_remove[0])
    #                             # Remove reaction
    #                             await ras_preview_window.remove_reaction(option_to_remove[0], self.bot.user)
    #
    #                             # update preview window
    #                             option_text = self.option_text(options_strings)
    #                             new_ras_session_embed.set_field_at(0,
    #                                                                name='\nCurrent options:',
    #                                                                value=option_text, inline=False)
    #                             # Update option list in preview window
    #                             await ras_preview_window.edit(embed=new_ras_session_embed)
    #
    #             elif self.word_check(response.content, 'done'):  # Check for 'done'
    #                 retry = False
    #
    #                 # Change create window tip back to basic message
    #                 create_embed.set_field_at(1, name='tip:',
    #                                           value='Type `cancel` at anytime to stop', inline=False)
    #                 # Remove preview of options from RAS preview
    #                 new_ras_session_embed.remove_field(0)
    #                 # Update preview window
    #                 await ras_preview_window.edit(embed=new_ras_session_embed)
    #             else:
    #                 # Make sure role mention is detected and get first one
    #                 if len(response.role_mentions) > 0:
    #                     items = response.content.split(' ')
    #                     emote = items[0]  # Get emote text
    #                     role = response.role_mentions[0]  # Get first role
    #                     # Check if role is valid
    #                     if role in ctx.message.guild.roles:
    #                         # Check if that is being inserted already exists in session
    #                         result = [i for i in new_ras_session.options if i['role'] == role]
    #                         if len(result) < 1:
    #                             try:
    #                                 # Try to add emote, if there is an exception, the emote is invalid
    #                                 await ras_preview_window.add_reaction(emote)
    #                                 # If add reaction succeeds add to session model
    #                                 await new_ras_session.add_option(emote, role)
    #                                 # Update option list
    #                                 options_strings.append([emote, role])
    #                                 option_text = self.option_text(options_strings)
    #                                 new_ras_session_embed.set_field_at(0,
    #                                                                    name='\nCurrent options:',
    #                                                                    value=option_text, inline=False)
    #                                 # Update option list in preview window
    #                                 await ras_preview_window.edit(embed=new_ras_session_embed)
    #                             except discord.HTTPException:
    #                                 await ctx.send('ERROR: Emoji is invalid')
    #                             except discord.DiscordException as e:
    #                                 print(e)
    #                         else:
    #                             await ctx.send('ERROR: An option already exists with that role')
    #                     else:
    #                         await ctx.send('ERROR: Could not validate role')
    #                 # Assume you want to add action with no role attached
    #                 elif len(response.role_mentions) < 1:
    #                     emote = response.content.strip(' ')
    #                     try:
    #                         # Try to add emote, if there is an exception, the emote is invalid
    #                         await ras_preview_window.add_reaction(emote)
    #                         # If add reaction succeeds add to session model
    #                         await new_ras_session.add_option(emote, None)
    #                         # Update option list
    #                         options_strings.append([emote, 'N/A'])
    #                         option_text = self.option_text(options_strings)
    #                         new_ras_session_embed.set_field_at(0,
    #                                                            name='\nCurrent options:',
    #                                                            value=option_text, inline=False)
    #                         # Update option list in preview window
    #                         await ras_preview_window.edit(embed=new_ras_session_embed)
    #                     except discord.HTTPException:
    #                         await ctx.send('ERROR: Emoji is invalid')
    #                     except discord.DiscordException as e:
    #                         print(e)
    #                 # else:
    #                 #     await ctx.send('ERROR: Invalid format detected, please look at example above.')
    #     except asyncio.TimeoutError:
    #         await self.timeout_embed(create_embed, create_ras_window, ras_preview_window,
    #                                  title='Create RAS :octagonal_sign:',
    #                                  text='This Create RAS session has timed out, please use the \'c!create\' command '
    #                                       'again ')
    #         return self.TIMEOUT
    #
    #     """############################################
    #     # Ask for Unique option
    #     ############################################"""
    #     # Change create RAS window
    #     create_embed.title = 'Create RAS - Step 4/?'
    #     create_embed.description = f'{ctx.message.author.name}, Do you want the roles to be unique? (yes/no)'
    #     create_embed.set_field_at(0, name='Example:',
    #                               value='Yes - Only one role will be assigned at a time\nNo - Multiple Roles can be '
    #                                     'assigned from this RAS',
    #                               inline=False)
    #     await create_ras_window.edit(embed=create_embed)
    #
    #     # Wait for response from author
    #     # see message_check() in step 2
    #     try:
    #         retry = True
    #         while retry is True:
    #             response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)
    #             if self.word_check(response.content, 'cancel'):
    #                 await self.cancel_embed(create_embed, create_ras_window, ras_preview_window,
    #                                         title='Create RAS :warning:',
    #                                         text='This create RAS sessions was cancelled, use the create command'
    #                                              ' again to start another session.')
    #                 return self.CANCEL
    #             elif self.word_check(response.content, 'yes') or self.word_check(response.content, 'no'):
    #                 retry = False
    #                 if self.word_check(response.content, 'yes'):
    #                     new_ras_session.unique = True
    #                     new_ras_session_embed.set_footer(text=f'Unique={True}')
    #                 elif self.word_check(response.content, 'no'):
    #                     new_ras_session.unique = False
    #                     new_ras_session_embed.set_footer(text=f'Unique={False}')
    #                 await ras_preview_window.edit(embed=new_ras_session_embed)
    #             else:
    #                 await ctx.send('Invalid format detected, please look at example above.')
    #
    #     except asyncio.TimeoutError:
    #         await self.timeout_embed(create_embed, create_ras_window, ras_preview_window,
    #                                  title='Create RAS :octagonal_sign:',
    #                                  text='This Create RAS session has timed out, please use the \'c!create\' command '
    #                                       'again ')
    #         return self.TIMEOUT
    #
    #     """############################################
    #     # Color
    #     ############################################"""
    #     # Change create RAS window
    #     create_embed.title = 'Create RAS - Step 6/?'
    #     create_embed.description = f'{ctx.message.author.name}, please choose the color you want to associate with ' \
    #                                f'this RAS in this format `[0-255],[0-255],[0-255]` See tip for example.'
    #     create_embed.set_field_at(0, name='Example:', value='`255,255,255`',
    #                               inline=False)
    #     create_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop, `done` when you are done',
    #                               inline=False)
    #     current_color = new_ras_session_embed.colour
    #     new_ras_session_embed.add_field(name='Current color:',
    #                                     value=f'{current_color.to_rgb()}', inline=False)
    #
    #     await create_ras_window.edit(embed=create_embed)
    #     await ras_preview_window.edit(embed=new_ras_session_embed)
    #
    #     # Wait for response from author
    #     # see message_check() in step 2
    #     try:
    #         retry = True
    #         while retry is True:
    #             response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)
    #             if self.word_check(response.content, 'cancel'):  # Check for 'cancel'
    #                 await self.cancel_embed(create_embed, create_ras_window, ras_preview_window,
    #                                         title='Create RAS :warning:',
    #                                         text='This create RAS sessions was cancelled, use the create command'
    #                                              ' again to start another session.')
    #                 return self.CANCEL
    #             elif self.word_check(response.content, 'done'):  # Check for 'done'
    #                 retry = False
    #
    #                 # Change create window tip back to basic message
    #                 create_embed.set_field_at(1, name='tip:',
    #                                           value='Type `cancel` at anytime to stop', inline=False)
    #                 # Remove preview of options from RAS preview
    #                 new_ras_session_embed.remove_field(0)
    #                 # Update preview window
    #                 await ras_preview_window.edit(embed=new_ras_session_embed)
    #             else:
    #                 new_color = self.color_atlas(response)
    #                 if new_color is not None:
    #                     new_ras_session_embed.colour = new_color
    #
    #                     new_ras_session_embed.set_field_at(0,
    #                                                        name='\nCurrent color:',
    #                                                        value=new_color.to_rgb(), inline=False)
    #                     await ras_preview_window.edit(embed=new_ras_session_embed)
    #
    #     except asyncio.TimeoutError:
    #         await self.timeout_embed(create_embed, create_ras_window, ras_preview_window,
    #                                  title='Create RAS :octagonal_sign:',
    #                                  text='This Create RAS session has timed out, please use the \'c!create\' command '
    #                                       'again ')
    #         return self.TIMEOUT
    #
    #     """############################################
    #     # Publish
    #     ############################################"""
    #     # Change create RAS window
    #     create_embed.title = 'Create RAS - Step 7/?'
    #     create_embed.description = f'{ctx.message.author.name},please confirm the preview below, then type `publish` ' \
    #                                f'or `cancel`'
    #     create_embed.clear_fields()
    #     await create_ras_window.edit(embed=create_embed)
    #
    #     # Wait for response from author
    #     # see message_check() in step 2
    #     try:
    #         retry = True
    #         while retry is True:
    #             response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)
    #             if self.word_check(response.content, 'cancel'):  # Listen for 'cancel'
    #                 await self.cancel_embed(create_embed, create_ras_window, ras_preview_window,
    #                                         title='Create RAS :warning:',
    #                                         text='This create RAS sessions was cancelled, use the create command'
    #                                              ' again to start another session.')
    #                 return self.CANCEL
    #             elif self.word_check(response.content, 'publish'):  # Listen for 'publish'
    #                 retry = False
    #                 # Publish to requested channel
    #                 published_context = await new_ras_session.channel.send(embed=new_ras_session_embed)
    #
    #                 # Add published message context to tracking
    #                 new_ras_session.message = published_context
    #
    #                 # Add reactions to publish RAS
    #                 for option in new_ras_session.options:
    #                     await published_context.add_reaction(option['emote'])
    #
    #                 # Delete preview window
    #                 await ras_preview_window.delete()
    #                 # TODO: Add list of what options are in confirmation
    #                 # Update create RAS form with confirmation
    #                 create_embed.title = 'Create RAS  -  :white_check_mark:'
    #                 create_embed.description = f'CONFIRMATION - The new RAS has been posted in ' \
    #                                            f'#{new_ras_session.channel}. If you would like to edit this RAS, you can' \
    #                                            f' use [coming soon :)] '
    #                 create_embed.colour = discord.Colour.green()
    #                 await create_ras_window.edit(embed=create_embed)
    #             else:
    #                 await ctx.send('Invalid format detected, please look at example above.')
    #     except asyncio.TimeoutError:
    #         await self.timeout_embed(create_embed, create_ras_window, ras_preview_window,
    #                                  title='Create RAS :octagonal_sign:',
    #                                  text='This Create RAS session has timed out, please use the \'c!create\' command '
    #                                       'again ')
    #         return self.TIMEOUT
    #
    #     # Save new RAS to memory
    #     self.ras_sessions.append(new_ras_session)
    #
    #     # Save session list to disk with new addition
    #     self.save_sessions_to_file()
    #
    #     # End routine
    #     return self.SUCCESS

    ####################
    # create() helpers #
    ####################

    # Parses options and returns string of options
    # format_type 0 does not account for a NONE type role

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
        if form_result is self.SUCCESS:
            self.save_sessions_to_file()
            return self.SUCCESS
        else:
            return form_result


    @staticmethod
    def option_text(options, format_type=0):
        if format_type == 0:
            if len(options) == 1:
                return options[0]
            else:
                option_text = options[0]
                count = 1
                while count < len(options):
                    # Check if the role text is 'N/A' for slightly different formatting
                    if options[count][1] == 'N/A':
                        option_text = option_text + f'{count}:  {options[count][0]} - [{options[count][1]}]\n'
                    else:
                        option_text = option_text + f'{count}:  {options[count][0]} - @{options[count][1]}\n'

                    count = count + 1
                return option_text
        elif format_type == 1:
            if len(options) < 1:
                return '(This will not display on final published RAS)\n'
            else:
                option_text = '(This will not display on final published RAS)\n'
                count = 0
                for opt in options:
                    if opt['role'] is None:
                        emote = opt['emote']
                        option_text = option_text + f'{count}:  {emote} - [N/A]\n'
                    else:
                        emote = opt['emote']
                        role = opt['role']
                        option_text = option_text + f'{count}:  {emote} - @{role}\n'
                    count = count + 1

                return option_text

    """#################################################
       edit() - Routine that contains logic for the RAS (Reaction-based role Assignment System) edit form.
       Helper function specific to edit() will be defined under this function
    #################################################"""

    async def edit(self, ctx, ras_to_edit):
        # Build preview based on RAS message context
        preview_window = None
        preview_ras_obj = copy.copy(ras_to_edit)
        preview_window_embed = copy.copy(ras_to_edit.message.embeds[0])
        preview_window_reactions = copy.copy(preview_ras_obj.message.reactions)
        preview_window_embed.set_footer(
            text=f'Unique={preview_ras_obj.unique} | Channel={preview_ras_obj.channel.name}')
        roles_to_remove = list()

        # Make EDIT_RAS message embed, add needed fields
        edit_window = None
        edit_embed = discord.Embed()
        edit_embed.colour = discord.Colour.blue()
        edit_embed.title = 'Edit RAS'  # Never changes, title of message
        edit_embed.description = f'Hello, {ctx.message.author.name}! Please choose what component you would' \
                                 f' like to edit:'  # Message block used by bot
        edit_embed.add_field(name='Components:', value='```1. Posted Channel\n2. Title/Description\n'
                                                       '3. Emotes/Roles\n4. Unique\n'
                                                       '5. Colour```', inline=False)
        edit_embed.add_field(name='tip:', value='Type `done` when you are done editing, or `cancel` at anytime to stop '
                                                '(*WILL NOT SAVE YOUR WORK*)',
                             inline=False)  # tips

        # Send update to edit window
        edit_window = await ctx.send(embed=edit_embed)

        # Send update to preview window
        preview_window = await ctx.send('Preview:\n', embed=preview_window_embed)

        # Wait for response from author
        # message_check() used to check if author responded in correct channel
        def message_check(message):
            is_author = message.author == ctx.message.author
            is_correct_guild = message.guild == ctx.message.guild
            in_correct_channel = message.channel == ctx.message.channel
            return is_author and in_correct_channel and is_correct_guild

        try:
            while True:

                # Update windows with Main Menu
                edit_embed.description = f'Hello, {ctx.message.author.name}! Please choose what component you would' \
                                         f' like to edit:'
                edit_embed.set_field_at(0, name='Components:', value='```1. Posted Channel\n2. Title/Description\n'
                                                                     '3. Emotes/Roles\n4. Unique\n'
                                                                     '5. Colour```', inline=False)
                edit_embed.set_field_at(1, name='tip:',
                                        value='Type `done` when you are done editing, or `cancel` at anytime to stop '
                                              '(*WILL NOT SAVE YOUR WORK*)',
                                        inline=False)

                # Send update to edit window
                await edit_window.edit(embed=edit_embed)

                # Send update to preview window
                preview_window_embed.set_footer(
                    text=f'Unique={preview_ras_obj.unique} | Channel={preview_ras_obj.channel.name}')
                await preview_window.edit(embed=preview_window_embed)

                # Add reactions
                current_state_preview_window = await ctx.channel.fetch_message(preview_window.id)
                for option in preview_ras_obj.options:
                    match = discord.utils.find(lambda r: r.emoji == option['emote'], current_state_preview_window.reactions)
                    print(f'1: {match}')
                    if match is None:
                        await preview_window.add_reaction(option['emote'])

                # Remove reactions not needed
                for reaction in current_state_preview_window.reactions:
                    match = discord.utils.find(lambda o: o['emote'] == reaction.emoji, preview_ras_obj.options)
                    if match is None:
                        await preview_window.clear_reaction(reaction.emoji)

                response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)
                if self.word_check(response.content, 'cancel'):
                    await self.cancel_embed(edit_embed, edit_window, preview_window, title='Edit RAS :warning:',
                                            text='The edit RAS was cancelled. Your work was **not** saved')
                    return self.CANCEL

                elif self.word_check(response.content, 'sink'):
                    # Delete old messages
                    await edit_window.delete()
                    await preview_window.delete()

                    # Send new ones
                    edit_window = await ctx.send(embed=edit_embed)
                    preview_window = await ctx.send('Preview:\n', embed=preview_window_embed)
                    for reaction in preview_window_reactions:
                        await preview_window.add_reaction(reaction.emoji)

                elif self.word_check(response.content, 'done'):
                    # show publish form
                    """###################################
                    # Confirm Changes
                    ###################################"""
                    edit_embed.title = 'Edit RAS - Please confirm your changes'
                    edit_embed.description = f'Hello, {ctx.message.author.name}! Type `publish` to complete this form, ' \
                                             f'or `cancel` to discard all changes.'
                    edit_embed.remove_field(0)
                    edit_embed.remove_field(0)

                    # Sink all messages to ensure user can see all information
                    await edit_window.delete()
                    # save reactions before deleting
                    preview_window_reactions = copy.copy(preview_window.reactions)
                    await preview_window.delete()

                    edit_window = await ctx.send(embed=edit_embed)

                    preview_window = await ctx.send('NEW: ', embed=preview_window_embed)
                    for option in preview_ras_obj.options:
                        await preview_window.add_reaction(option['emote'])

                    old_ras_message = await self.bot.get_channel(ras_to_edit.channel.id).fetch_message(
                        ras_to_edit.message.id)
                    old_preview_window = await ctx.send('OLD: ', embed=ras_to_edit.message.embeds[0])
                    for reaction in old_ras_message.reactions:
                        await old_preview_window.add_reaction(reaction.emoji)

                    try:
                        retry = True
                        while retry is True:

                            response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)

                            if self.word_check(response.content, 'cancel'):
                                await self.cancel_embed(edit_embed, edit_window, preview_window,
                                                        title='Edit RAS :warning:',
                                                        text='The edit RAS was cancelled. Your work was **not** saved')
                                await old_preview_window.delete()
                                return self.CANCEL
                            elif self.word_check(response.content, 'publish'):
                                # Apply following changes:
                                # new embed
                                await ras_to_edit.message.edit(embed=preview_window_embed)
                                # unique state
                                ras_to_edit.unique = preview_ras_obj.unique
                                # check reactions
                                ras_to_edit.options = preview_ras_obj.options

                                # Add reactions
                                for option in ras_to_edit.options:
                                    await ras_to_edit.message.add_reaction(option['emote'])

                                # Remove reactions not needed
                                current_message_state_ras_to_edit = await ras_to_edit.channel.fetch_message(
                                    ras_to_edit.message.id)
                                for reaction in current_message_state_ras_to_edit.reactions:
                                    match = discord.utils.find(lambda o: o['emote'] == reaction.emoji,
                                                               ras_to_edit.options)

                                    if match is None:
                                        await ras_to_edit.message.clear_reaction(reaction.emoji)

                                # Clear roles for removed reaction
                                for role in roles_to_remove:
                                    guild_role = discord.utils.find(lambda r: r == role,
                                                                    current_message_state_ras_to_edit.guild.roles)
                                    if guild_role is not None:
                                        for member in guild_role.members:
                                            await member.remove_roles(role)

                                # Move channel
                                if ras_to_edit.channel is not preview_ras_obj.channel:
                                    new_message_ctx = await preview_ras_obj.channel.send(
                                        embed=current_message_state_ras_to_edit.embeds[0])

                                    if new_message_ctx is not None:
                                        for option in ras_to_edit.options:
                                            await new_message_ctx.add_reaction(option['emote'])
                                        await ras_to_edit.message.delete()
                                        ras_to_edit.channel = new_message_ctx.channel
                                        ras_to_edit.message = new_message_ctx
                                    else:
                                        await ctx.send("Error moving RAS to another channel")

                                retry = False
                                editing_ras = False

                                await old_preview_window.delete()
                                await preview_window.delete()

                                edit_embed.title = 'Edit RAS  -  :white_check_mark:'
                                edit_embed.description = f'CONFIRMATION'
                                edit_embed.colour = discord.Colour.green()
                                await edit_window.edit(embed=edit_embed)

                                # Save session list to disk
                                self.save_sessions_to_file()

                                # Validate message
                                message_id = ras_to_edit.message.id
                                await self.validate_state(scope='message', id_list=[message_id])

                                return self.SUCCESS

                    except asyncio.TimeoutError:
                        await self.timeout_embed(edit_embed, edit_window, preview_window,
                                                 title='Edit RAS :octagonal_sign:',
                                                 text='This edit RAS session has timed out, please use the '
                                                      'previous command '
                                                      'to try again.')
                        return self.TIMEOUT

                else:
                    # Ask for channel/guild
                    if self.word_check(response.content, '1'):
                        """###################################
                        # Ask for channel/guild
                        ###################################"""
                        edit_embed.title = 'Edit RAS - Change Channel'
                        edit_embed.description = f'Hello, {ctx.message.author.name}! Please enter the channel you ' \
                                                 f'would like to see the RAS in. \n```diff\n-THIS WILL CLEAR ALL REACTIONS. ' \
                                                 f' Roles will be maintained on move.```'
                        edit_embed.set_field_at(0, name='Example:', value='`#example_channel`', inline=False)
                        edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                                      '(*WILL NOT SAVE YOUR WORK*), or '
                                                                      '`done` to save this change',
                                                inline=False)
                        await edit_window.edit(embed=edit_embed)

                        current_channel = ras_to_edit.channel

                        preview_window_embed.insert_field_at(0, name='Current option (Will not appear in final RAS):',
                                                             value='N/A')

                        try:
                            retry = True
                            while retry is True:

                                preview_window_embed.set_field_at(0, name='Current option:',
                                                                  value='(Will not appear in final RAS)\n'
                                                                        f'`#{current_channel.name}`')
                                await preview_window.edit(embed=preview_window_embed)

                                response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)

                                if self.word_check(response.content, 'cancel'):
                                    retry = False
                                    preview_window_embed.remove_field(0)
                                elif self.word_check(response.content, 'done'):
                                    retry = False
                                    preview_ras_obj.channel = current_channel
                                    preview_ras_obj.guild = response.guild
                                    preview_window_embed.remove_field(0)
                                elif len(response.channel_mentions) > 0:
                                    if response.channel_mentions[0] in ctx.message.guild.channels:
                                        current_channel = response.channel_mentions[0]
                                else:
                                    await ctx.send('Unable to verify channel')

                        except asyncio.TimeoutError:

                            await self.timeout_embed(edit_embed, edit_window, preview_window,
                                                     title='Edit RAS :octagonal_sign:',
                                                     text='This edit RAS session has timed out, please use the '
                                                          'previous command '
                                                          'to try again.')
                            return self.TIMEOUT
                    # Title/desc
                    elif self.word_check(response.content, '2'):
                        """###################################
                        # Ask for title/desc
                        ###################################"""
                        edit_embed.title = 'Edit RAS - Change title and description'
                        edit_embed.description = f'Hello, {ctx.message.author.name}! Please enter the title and ' \
                                                 f'description you would like to see in the RAS.'
                        edit_embed.set_field_at(0, name='Example:', value='`title here | description here`',
                                                inline=False)
                        edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                                      '(*WILL NOT SAVE YOUR WORK*), or '
                                                                      '`done` to save this change',
                                                inline=False)
                        await edit_window.edit(embed=edit_embed)

                        default_title = preview_window_embed.title
                        default_description = preview_window_embed.description

                        try:
                            retry = True
                            while retry is True:

                                response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)

                                if self.word_check(response.content, 'cancel'):
                                    retry = False
                                    preview_window_embed.title = default_title
                                    preview_window_embed.description = default_description
                                elif self.word_check(response.content, 'done'):
                                    retry = False
                                elif self.verify_title_desc(response.content):
                                    items = response.content.split('|')
                                    preview_window_embed.title = items[0].strip()
                                    preview_window_embed.description = items[1].strip()
                                    await preview_window.edit(embed=preview_window_embed)
                                else:
                                    await ctx.send('Invalid format')

                        except asyncio.TimeoutError:

                            await self.timeout_embed(edit_embed, edit_window, preview_window,
                                                     title='Edit RAS :octagonal_sign:',
                                                     text='This edit RAS session has timed out, please use the '
                                                          'previous command '
                                                          'to try again.')
                            return self.TIMEOUT
                    # Emote/role
                    elif self.word_check(response.content, '3'):
                        # emote/roles
                        """###################################
                        # Edit emote/role options
                        ###################################"""
                        edit_embed.title = 'Edit RAS - Options'
                        edit_embed.description = f'{ctx.message.author.name}, please list out the reaction/roles you' \
                                                 f' would like to add: \n[:the_emote:]\' \'[@role]. To delete a ' \
                                                 f'line type \'del [int]\''
                        edit_embed.set_field_at(0, name='Example:',
                                                value='`:warning: @spoiler_squad`\n`del 1`',
                                                inline=False)
                        edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                                      '(*WILL NOT SAVE YOUR WORK*), or '
                                                                      '`done` to save this change',
                                                inline=False)
                        await edit_window.edit(embed=edit_embed)

                        preview_window_embed.add_field(name='Current options:', value='None', inline=False)

                        default_options = copy.copy(preview_ras_obj.options)

                        # update preview window
                        option_text = self.option_text(preview_ras_obj.options, format_type=1)
                        preview_window_embed.set_field_at(0,
                                                          name='\nCurrent options:',
                                                          value=option_text, inline=False)
                        # Update option list in preview window
                        await preview_window.edit(embed=preview_window_embed)

                        try:
                            retry = True
                            while retry is True:

                                response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)

                                if self.word_check(response.content, 'cancel'):
                                    retry = False
                                    preview_ras_obj.options = default_options
                                    preview_window_embed.remove_field(0)
                                elif self.word_check(response.content, 'done'):
                                    retry = False
                                    preview_window_embed.remove_field(0)

                                elif self.word_check(response.content, 'del'):
                                    # Get first argument after delete
                                    arg = response.content.strip(' ').split(' ')
                                    if len(arg) > 1:
                                        arg = arg[1].strip(' ')
                                        # Check if is int
                                        if self.is_int(arg) is True:
                                            delete_option = int(arg)
                                            if 0 <= delete_option < len(preview_ras_obj.options):
                                                # Remove from option list
                                                option_to_remove = preview_ras_obj.options.pop(delete_option)

                                                if option_to_remove['role'] not in roles_to_remove:
                                                    roles_to_remove.append(option_to_remove['role'])

                                                # Remove reaction
                                                await preview_window.remove_reaction(option_to_remove['emote'],
                                                                                     self.bot.user)

                                                # update preview window
                                                option_text = self.option_text(preview_ras_obj.options, format_type=1)
                                                preview_window_embed.set_field_at(0,
                                                                                  name='\nCurrent options:',
                                                                                  value=option_text, inline=False)
                                                # Update option list in preview window
                                                await preview_window.edit(embed=preview_window_embed)
                                else:
                                    # Make sure role mention is detected and get first one
                                    if len(response.role_mentions) > 0:
                                        items = response.content.split(' ')
                                        emote = items[0]  # Get emote text
                                        role = response.role_mentions[0]  # Get first role
                                        # Check if role is valid
                                        if role in ctx.message.guild.roles:
                                            # Check if that is being inserted already exists in session
                                            result = [i for i in preview_ras_obj.options if i['role'] == role]
                                            if len(result) < 1:
                                                try:
                                                    # Try to add emote, if there is an exception, the emote is invalid
                                                    await preview_window.add_reaction(emote)
                                                    # If add reaction succeeds add to session model
                                                    await preview_ras_obj.add_option(emote, role)

                                                    if role in roles_to_remove:
                                                        roles_to_remove.remove(role)

                                                    option_text = self.option_text(preview_ras_obj.options,
                                                                                   format_type=1)
                                                    preview_window_embed.set_field_at(0,
                                                                                      name='\nCurrent options:',
                                                                                      value=option_text, inline=False)
                                                    # Update option list in preview window
                                                    await preview_window.edit(embed=preview_window_embed)
                                                except discord.HTTPException:
                                                    await ctx.send('ERROR: Emoji is invalid')
                                                except discord.DiscordException as e:
                                                    print(e)
                                            else:
                                                await ctx.send('ERROR: An option already exists with that role')
                                        else:
                                            await ctx.send('ERROR: Could not validate role')
                                    # Assume you want to add action with no role attached
                                    elif len(response.role_mentions) < 1:
                                        emote = response.content.strip(' ')
                                        try:
                                            # Try to add emote, if there is an exception, the emote is invalid
                                            await preview_window.add_reaction(emote)
                                            # If add reaction succeeds add to session model
                                            await preview_ras_obj.add_option(emote, None)

                                            option_text = self.option_text(preview_ras_obj.options, format_type=1)
                                            preview_window_embed.set_field_at(0,
                                                                              name='\nCurrent options:',
                                                                              value=option_text, inline=False)
                                            # Update option list in preview window
                                            await preview_window.edit(embed=preview_window_embed)
                                        except discord.HTTPException:
                                            await ctx.send('ERROR: Emoji is invalid')
                                        except discord.DiscordException as e:
                                            print(e)

                        except asyncio.TimeoutError:

                            await self.timeout_embed(edit_embed, edit_window, preview_window,
                                                     title='Edit RAS :octagonal_sign:',
                                                     text='This edit RAS session has timed out, please use the '
                                                          'previous command '
                                                          'to try again.')
                            return self.TIMEOUT
                    # Unique
                    elif self.word_check(response.content, '4'):
                        # unique
                        """###################################
                        # Ask if RAS will be Unique
                        ###################################"""
                        edit_embed.title = 'Edit RAS - Unique'
                        edit_embed.description = f'Hello, {ctx.message.author.name}! Please enter yes or no if you ' \
                                                 f'want the RAS to use unique role options.'
                        edit_embed.set_field_at(0, name='Example:',
                                                value='Yes - Only one role will be assigned at a time\n'
                                                      'No - Multiple Roles can be '
                                                      'assigned from this RAS',
                                                inline=False)
                        edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                                      '(*WILL NOT SAVE YOUR WORK*), or '
                                                                      '`done` to save this change',
                                                inline=False)
                        await edit_window.edit(embed=edit_embed)

                        default_unique = preview_ras_obj.unique

                        try:
                            retry = True
                            while retry is True:

                                response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)

                                if self.word_check(response.content, 'cancel'):
                                    retry = False
                                    preview_ras_obj.unique = default_unique
                                elif self.word_check(response.content, 'done'):
                                    retry = False
                                elif self.word_check(response.content, 'yes'):
                                    preview_ras_obj.unique = True
                                    preview_window_embed.set_footer(
                                        text=f'Unique={preview_ras_obj.unique} | Channel={preview_ras_obj.channel.name}')
                                    await preview_window.edit(embed=preview_window_embed)
                                elif self.word_check(response.content, 'no'):
                                    preview_ras_obj.unique = False
                                    preview_window_embed.set_footer(
                                        text=f'Unique={preview_ras_obj.unique} | Channel={preview_ras_obj.channel.name}')
                                    await preview_window.edit(embed=preview_window_embed)

                        except asyncio.TimeoutError:

                            await self.timeout_embed(edit_embed, edit_window, preview_window,
                                                     title='Edit RAS :octagonal_sign:',
                                                     text='This edit RAS session has timed out, please use the '
                                                          'previous command '
                                                          'to try again.')
                            return self.TIMEOUT
                    # Colour
                    elif self.word_check(response.content, '5'):
                        # colour
                        """###################################
                        # Set colour of RAS
                        ###################################"""
                        retry = True
                        edit_embed.title = 'Edit RAS - Colour'
                        edit_embed.description = f'{ctx.message.author.name}, please choose the color you want to ' \
                                                 f'associate with this RAS in this format `[0-255],[0-255],[0-255]` ' \
                                                 f'See tip for example.'
                        edit_embed.set_field_at(0, name='Example:',
                                                value='`255,255,255`',
                                                inline=False)
                        edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                                      '(*WILL NOT SAVE YOUR WORK*), or '
                                                                      '`done` to save this change',
                                                inline=False)
                        await edit_window.edit(embed=edit_embed)

                        if preview_window_embed.colour is not discord.Embed.Empty:
                            default_colour = preview_window_embed.colour
                        else:
                            default_colour = discord.Colour.from_rgb(32, 34, 37)
                            preview_window_embed.colour = default_colour

                        preview_window_embed.insert_field_at(0, name='Current colour',
                                                             value=f'{default_colour.to_rgb()}')

                        await preview_window.edit(embed=preview_window_embed)

                        try:
                            while retry is True:
                                response = await self.bot.wait_for('message', timeout=self.timeout, check=message_check)

                                if self.word_check(response.content, 'cancel'):
                                    retry = False
                                    preview_window_embed.remove_field(0)
                                    preview_window_embed.colour = default_colour
                                elif self.word_check(response.content, 'done'):
                                    retry = False
                                    preview_window_embed.remove_field(0)
                                else:
                                    new_color = self.color_atlas(response)
                                    if new_color is not None:
                                        preview_window_embed.colour = new_color

                                        preview_window_embed.set_field_at(0,
                                                                          name='Current color:',
                                                                          value=new_color.to_rgb(), inline=False)
                                        await preview_window.edit(embed=preview_window_embed)

                        except asyncio.TimeoutError:

                            await self.timeout_embed(edit_embed, edit_window, preview_window,
                                                     title='Edit RAS :octagonal_sign:',
                                                     text='This edit RAS session has timed out, please use the '
                                                          'previous command '
                                                          'to try again.')
                            return self.TIMEOUT
        except asyncio.TimeoutError:
            await self.timeout_embed(edit_embed, edit_window, preview_window, title='Edit RAS :octagonal_sign:',
                                     text='This edit RAS session has timed out, please use the previous command '
                                          ' to try again.')
            return self.TIMEOUT

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
                    return self.CANCEL
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

                        return self.SUCCESS
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
                        return self.FAILURE
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
                        return self.FAILURE
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
                        return self.FAILURE
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
                        return self.FAILURE
        except asyncio.TimeoutError:

            await self.timeout_embed(delete_embed, delete_window, preview_window,
                                     title='Delete RAS :octagonal_sign:',
                                     text='This delete RAS session has timed out, please use the '
                                          'previous command '
                                          'to try again.')
            return self.TIMEOUT

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

                # Add users who have not reacted but, have roles associated with the RAS
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
