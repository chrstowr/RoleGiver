import asyncio
import copy
import discord

from RoleGiver.Services.GeneralServices import RGServices
from RoleGiver.Views.DiscordEmbeds import RGEmbeds
from RoleGiver.Models.StatusEnum import Status


class EditForm:

    def __init__(self, bot, ctx, ras_to_edit):
        self.bot = bot
        self.ctx = ctx
        self.ras_to_edit = ras_to_edit
        self.timeout = 320.00

        # Build preview based on RAS message context
        self.preview_window = None
        self.preview_ras_obj = copy.copy(ras_to_edit)
        self.preview_window_embed = copy.copy(self.ras_to_edit.message.embeds[0])
        self.preview_window_reactions = copy.copy(self.preview_ras_obj.message.reactions)
        self.preview_window_embed.set_footer(
            text=f'Unique={self.preview_ras_obj.unique} | Channel={self.preview_ras_obj.channel.name}')
        self.roles_to_remove = list()

        # Make EDIT_RAS message embed, add needed fields
        self.edit_window = None
        self.edit_embed = discord.Embed()
        self.edit_embed.colour = discord.Colour.blue()
        self.edit_embed.title = 'Edit RAS'  # Never changes, title of message
        self.edit_embed.description = f'Hello, {self.ctx.message.author.name}! Please choose what component you would' \
                                      f' like to edit:'  # Message block used by bot
        self.edit_embed.add_field(name='Components:', value='N/A', inline=False)
        self.edit_embed.add_field(name='tip:',
                                  value='Type `done` when you are done editing, or `cancel` at anytime to stop '
                                        '(*WILL NOT SAVE YOUR WORK*)',
                                  inline=False)  # tips

        self.form_queue = list()

    def add_step(self, func, desc):
        self.form_queue.append([func, desc])

    async def run(self):
        # Send update to edit window
        self.edit_window = await self.ctx.send(embed=self.edit_embed)

        # Send update to preview window
        self.preview_window = await self.ctx.send('Preview:\n', embed=self.preview_window_embed)

        try:
            while True:

                # Update windows with Main Menu
                self.edit_embed.description = f'Hello, {self.ctx.message.author.name}! ' \
                                              f'Please choose what component you would like to edit:'

                # Generate option's list
                option_list = "```"
                count = 0
                for step in self.form_queue:
                    option_list = option_list + f"{count}. {step[1]}\n"
                    count = count + 1
                option_list = option_list + "```"

                self.edit_embed.set_field_at(0, name='Components:', value=option_list, inline=False)
                self.edit_embed.set_field_at(1, name='tip:',
                                             value='Type `done` when you are done editing, or `cancel` at anytime to stop '
                                                   '(*WILL NOT SAVE YOUR WORK*)',
                                             inline=False)

                # Send update to edit window
                await self.edit_window.edit(embed=self.edit_embed)

                # Send update to preview window
                self.preview_window_embed.set_footer(
                    text=f'Unique={self.preview_ras_obj.unique} | Channel={self.preview_ras_obj.channel.name}')
                await self.preview_window.edit(embed=self.preview_window_embed)

                # Add reactions
                current_state_preview_window = await self.ctx.channel.fetch_message(self.preview_window.id)
                for option in self.preview_ras_obj.options:
                    match = discord.utils.find(lambda r: r.emoji == option['emote'],
                                               current_state_preview_window.reactions)
                    if match is None:
                        await self.preview_window.add_reaction(option['emote'])

                # Remove reactions not needed
                for reaction in current_state_preview_window.reactions:
                    match = discord.utils.find(lambda o: o['emote'] == reaction.emoji, self.preview_ras_obj.options)
                    if match is None:
                        await self.preview_window.clear_reaction(reaction.emoji)

                response = await self.bot.wait_for('message', timeout=self.timeout, check=self.message_check)

                if RGServices().word_check(response.content, 'cancel'):
                    await RGEmbeds.cancel_embed(self.edit_embed, self.edit_window, self.preview_window,
                                                title='Edit RAS :warning:',
                                                text='The edit RAS was cancelled. Your work was **not** saved')
                    return Status.CANCEL

                elif RGServices().word_check(response.content, 'sink'):
                    # Delete old messages
                    await self.edit_window.delete()
                    await self.preview_window.delete()

                    # Send new ones
                    self.edit_window = await self.ctx.send(embed=self.edit_embed)
                    self.preview_window = await self.ctx.send('Preview:\n', embed=self.preview_window_embed)
                    for reaction in self.preview_window_reactions:
                        await self.preview_window.add_reaction(reaction.emoji)

                elif RGServices().word_check(response.content, 'done'):

                    result = await self.publish()
                    if result is not Status.CANCEL:
                        return result
                else:
                    if RGServices.is_int(response.content):
                        option_chosen = int(response.content)
                        if 0 <= option_chosen < len(self.form_queue):
                            result = await self.form_queue[option_chosen][0]()
                            if result is Status.TIMEOUT:
                                return result

                    pass
        except asyncio.TimeoutError:
            await RGEmbeds.timeout_embed(self.edit_embed, self.edit_window, self.preview_window,
                                         title='Edit RAS :octagonal_sign:',
                                         text='This edit RAS session has timed out, please use the previous command '
                                              ' to try again.')
            return Status.TIMEOUT

    async def get_channel(self):
        """###################################
        # Ask for channel/guild
        ###################################"""
        self.edit_embed.title = 'Edit RAS - Change Channel'
        self.edit_embed.description = f'Hello, {self.ctx.message.author.name}! Please enter the channel you ' \
                                      f'would like to see the RAS in. \n```diff\n-THIS WILL CLEAR ALL REACTIONS. ' \
                                      f' Roles will be maintained on move.```'
        self.edit_embed.set_field_at(0, name='Example:', value='`#example_channel`', inline=False)
        self.edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                           '(*WILL NOT SAVE YOUR WORK*), or '
                                                           '`done` to save this change',
                                     inline=False)
        await self.edit_window.edit(embed=self.edit_embed)

        current_channel = self.ras_to_edit.channel

        self.preview_window_embed.insert_field_at(0,
                                                  name='Current option (Will not appear in final RAS):',
                                                  value='N/A')

        try:
            while True:

                self.preview_window_embed.set_field_at(0, name='Current option:',
                                                       value='(Will not appear in final RAS)\n'
                                                             f'`#{current_channel.name}`')
                await self.preview_window.edit(embed=self.preview_window_embed)

                response = await self.bot.wait_for('message', timeout=self.timeout,
                                                   check=self.message_check)

                if RGServices().word_check(response.content, 'cancel'):
                    self.preview_window_embed.remove_field(0)
                    return
                elif RGServices().word_check(response.content, 'done'):
                    self.preview_ras_obj.channel = current_channel
                    self.preview_ras_obj.guild = response.guild
                    self.preview_window_embed.remove_field(0)
                    return
                elif len(response.channel_mentions) > 0:
                    if response.channel_mentions[0] in self.ctx.message.guild.channels:
                        current_channel = response.channel_mentions[0]
                else:
                    await self.ctx.send('Unable to verify channel')

        except asyncio.TimeoutError:

            await RGEmbeds.timeout_embed(self.edit_embed, self.edit_window, self.preview_window,
                                         title='Edit RAS :octagonal_sign:',
                                         text='This edit RAS session has timed out, please use the '
                                              'previous command '
                                              'to try again.')
            return Status.TIMEOUT

    async def get_title_desc(self):
        """###################################
        # Ask for title/desc
        ###################################"""
        self.edit_embed.title = 'Edit RAS - Change title and description'
        self.edit_embed.description = f'Hello, {self.ctx.message.author.name}! Please enter the title and ' \
                                      f'description you would like to see in the RAS.'
        self.edit_embed.set_field_at(0, name='Example:', value='`title here | description here`',
                                     inline=False)
        self.edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                           '(*WILL NOT SAVE YOUR WORK*), or '
                                                           '`done` to save this change',
                                     inline=False)
        await self.edit_window.edit(embed=self.edit_embed)

        default_title = self.preview_window_embed.title
        default_description = self.preview_window_embed.description

        try:
            while True:

                response = await self.bot.wait_for('message', timeout=self.timeout,
                                                   check=self.message_check)

                if RGServices().word_check(response.content, 'cancel'):
                    self.preview_window_embed.title = default_title
                    self.preview_window_embed.description = default_description
                    return
                elif RGServices().word_check(response.content, 'done'):
                    return
                elif RGServices().verify_title_desc(response.content):
                    items = response.content.split('|')
                    self.preview_window_embed.title = items[0].strip()
                    self.preview_window_embed.description = items[1].strip()
                    await self.preview_window.edit(embed=self.preview_window_embed)
                else:
                    await self.ctx.send('Invalid format')

        except asyncio.TimeoutError:

            await RGEmbeds.timeout_embed(self.edit_embed, self.edit_window, self.preview_window,
                                         title='Edit RAS :octagonal_sign:',
                                         text='This edit RAS session has timed out, please use the '
                                              'previous command '
                                              'to try again.')
            return Status.TIMEOUT

    async def get_emote_role(self):
        # emote/roles
        """###################################
        # Edit emote/role options
        ###################################"""
        self.edit_embed.title = 'Edit RAS - Options'
        self.edit_embed.description = f'{self.ctx.message.author.name}, please list out the reaction/roles you' \
                                      f' would like to add: \n[:the_emote:]\' \'[@role]. To delete a ' \
                                      f'line type \'del [int]\''
        self.edit_embed.set_field_at(0, name='Example:',
                                     value='`:warning: @spoiler_squad`\n`del 1`',
                                     inline=False)
        self.edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                           '(*WILL NOT SAVE YOUR WORK*), or '
                                                           '`done` to save this change',
                                     inline=False)
        await self.edit_window.edit(embed=self.edit_embed)

        self.preview_window_embed.add_field(name='Current options:', value='None', inline=False)

        default_options = copy.copy(self.preview_ras_obj.options)

        # update preview window
        option_text = RGServices().option_text(self.preview_ras_obj.options, format_type=1)
        self.preview_window_embed.set_field_at(0,
                                               name='\nCurrent options:',
                                               value=option_text, inline=False)
        # Update option list in preview window
        await self.preview_window.edit(embed=self.preview_window_embed)

        try:
            while True:

                response = await self.bot.wait_for('message', timeout=self.timeout,
                                                   check=self.message_check)

                if RGServices().word_check(response.content, 'cancel'):
                    self.preview_ras_obj.options = default_options
                    self.preview_window_embed.remove_field(0)
                    return
                elif RGServices().word_check(response.content, 'done'):
                    self.preview_window_embed.remove_field(0)
                    return
                elif RGServices().word_check(response.content, 'del'):
                    # Get first argument after delete
                    arg = response.content.strip(' ').split(' ')
                    if len(arg) > 1:
                        arg = arg[1].strip(' ')
                        # Check if is int
                        if RGServices().is_int(arg) is True:
                            delete_option = int(arg)
                            if 0 <= delete_option < len(self.preview_ras_obj.options):
                                # Remove from option list
                                option_to_remove = self.preview_ras_obj.options.pop(delete_option)

                                if option_to_remove['role'] not in self.roles_to_remove:
                                    self.roles_to_remove.append(option_to_remove['role'])

                                # Remove reaction
                                await self.preview_window.remove_reaction(option_to_remove['emote'],
                                                                          self.bot.user)

                                # update preview window
                                option_text = RGServices().option_text(self.preview_ras_obj.options,
                                                                       format_type=1)
                                self.preview_window_embed.set_field_at(0,
                                                                       name='\nCurrent options:',
                                                                       value=option_text, inline=False)
                                # Update option list in preview window
                                await self.preview_window.edit(embed=self.preview_window_embed)
                else:
                    # Make sure role mention is detected and get first one
                    if len(response.role_mentions) > 0:
                        items = response.content.split(' ')
                        emote = items[0]  # Get emote text
                        role = response.role_mentions[0]  # Get first role
                        # Check if role is valid
                        if role in self.ctx.message.guild.roles:
                            # Check if that is being inserted already exists in session
                            result = [i for i in self.preview_ras_obj.options if i['role'] == role]
                            if len(result) < 1:
                                try:
                                    # Try to add emote, if there is an exception, the emote is invalid
                                    await self.preview_window.add_reaction(emote)
                                    # If add reaction succeeds add to session model
                                    await self.preview_ras_obj.add_option(emote, role)

                                    if role in self.roles_to_remove:
                                        self.roles_to_remove.remove(role)

                                    option_text = RGServices().option_text(self.preview_ras_obj.options,
                                                                           format_type=1)
                                    self.preview_window_embed.set_field_at(0,
                                                                           name='\nCurrent options:',
                                                                           value=option_text,
                                                                           inline=False)
                                    # Update option list in preview window
                                    await self.preview_window.edit(embed=self.preview_window_embed)
                                except discord.HTTPException:
                                    await self.ctx.send('ERROR: Emoji is invalid')
                                except discord.DiscordException as e:
                                    print(e)
                            else:
                                await self.ctx.send('ERROR: An option already exists with that role')
                        else:
                            await self.ctx.send('ERROR: Could not validate role')
                    # Assume you want to add action with no role attached
                    elif len(response.role_mentions) < 1:
                        emote = response.content.strip(' ')
                        try:
                            # Try to add emote, if there is an exception, the emote is invalid
                            await self.preview_window.add_reaction(emote)
                            # If add reaction succeeds add to session model
                            await self.preview_ras_obj.add_option(emote, None)

                            option_text = RGServices().option_text(self.preview_ras_obj.options,
                                                                   format_type=1)
                            self.preview_window_embed.set_field_at(0,
                                                                   name='\nCurrent options:',
                                                                   value=option_text, inline=False)
                            # Update option list in preview window
                            await self.preview_window.edit(embed=self.preview_window_embed)
                        except discord.HTTPException:
                            await self.ctx.send('ERROR: Emoji is invalid')
                        except discord.DiscordException as e:
                            print(e)

        except asyncio.TimeoutError:

            await RGEmbeds.timeout_embed(self.edit_embed, self.edit_window, self.preview_window,
                                         title='Edit RAS :octagonal_sign:',
                                         text='This edit RAS session has timed out, please use the '
                                              'previous command '
                                              'to try again.')
            return Status.TIMEOUT

    async def get_unique_flag(self):
        """###################################
        # Ask if RAS will be Unique
        ###################################"""
        self.edit_embed.title = 'Edit RAS - Unique'
        self.edit_embed.description = f'Hello, {self.ctx.message.author.name}! Please enter yes or no if you ' \
                                      f'want the RAS to use unique role options.'
        self.edit_embed.set_field_at(0, name='Example:',
                                     value='Yes - Only one role will be assigned at a time\n'
                                           'No - Multiple Roles can be '
                                           'assigned from this RAS',
                                     inline=False)
        self.edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                           '(*WILL NOT SAVE YOUR WORK*), or '
                                                           '`done` to save this change',
                                     inline=False)
        await self.edit_window.edit(embed=self.edit_embed)

        default_unique = self.preview_ras_obj.unique

        try:
            while True:

                response = await self.bot.wait_for('message', timeout=self.timeout,
                                                   check=self.message_check)

                if RGServices().word_check(response.content, 'cancel'):
                    self.preview_ras_obj.unique = default_unique
                    return
                elif RGServices().word_check(response.content, 'done'):
                    return
                elif RGServices().word_check(response.content, 'yes'):
                    self.preview_ras_obj.unique = True
                    self.preview_window_embed.set_footer(
                        text=f'Unique={self.preview_ras_obj.unique} | Channel={self.preview_ras_obj.channel.name}')
                    await self.preview_window.edit(embed=self.preview_window_embed)
                elif RGServices().word_check(response.content, 'no'):
                    self.preview_ras_obj.unique = False
                    self.preview_window_embed.set_footer(
                        text=f'Unique={self.preview_ras_obj.unique} | Channel={self.preview_ras_obj.channel.name}')
                    await self.preview_window.edit(embed=self.preview_window_embed)

        except asyncio.TimeoutError:

            await RGEmbeds.timeout_embed(self.edit_embed, self.edit_window, self.preview_window,
                                         title='Edit RAS :octagonal_sign:',
                                         text='This edit RAS session has timed out, please use the '
                                              'previous command '
                                              'to try again.')
            return Status.TIMEOUT

    async def get_color(self):
        """###################################
        # Set colour of RAS
        ###################################"""
        self.edit_embed.title = 'Edit RAS - Colour'
        self.edit_embed.description = f'{self.ctx.message.author.name}, please choose the color you want to ' \
                                      f'associate with this RAS in this format `[0-255],[0-255],[0-255]` ' \
                                      f'See tip for example.'
        self.edit_embed.set_field_at(0, name='Example:',
                                     value='`255,255,255`',
                                     inline=False)
        self.edit_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop '
                                                           '(*WILL NOT SAVE YOUR WORK*), or '
                                                           '`done` to save this change',
                                     inline=False)
        await self.edit_window.edit(embed=self.edit_embed)

        if self.preview_window_embed.colour is not discord.Embed.Empty:
            default_colour = self.preview_window_embed.colour
        else:
            default_colour = discord.Colour.from_rgb(32, 34, 37)
            self.preview_window_embed.colour = default_colour

        self.preview_window_embed.insert_field_at(0, name='Current colour',
                                                  value=f'{default_colour.to_rgb()}')

        await self.preview_window.edit(embed=self.preview_window_embed)

        try:
            while True:
                response = await self.bot.wait_for('message', timeout=self.timeout,
                                                   check=self.message_check)

                if RGServices().word_check(response.content, 'cancel'):
                    self.preview_window_embed.remove_field(0)
                    self.preview_window_embed.colour = default_colour
                    return
                elif RGServices().word_check(response.content, 'done'):
                    self.preview_window_embed.remove_field(0)
                    return
                else:
                    new_color = RGServices().color_atlas(response)
                    if new_color is not None:
                        self.preview_window_embed.colour = new_color

                        self.preview_window_embed.set_field_at(0,
                                                               name='Current color:',
                                                               value=new_color.to_rgb(), inline=False)
                        await self.preview_window.edit(embed=self.preview_window_embed)

        except asyncio.TimeoutError:

            await RGEmbeds.timeout_embed(self.edit_embed, self.edit_window, self.preview_window,
                                         title='Edit RAS :octagonal_sign:',
                                         text='This edit RAS session has timed out, please use the '
                                              'previous command '
                                              'to try again.')
            return Status.TIMEOUT

    async def publish(self):
        """###################################
        # Confirm Changes
        ###################################"""
        self.edit_embed.title = 'Edit RAS - Please confirm your changes'
        self.edit_embed.description = f'Hello, {self.ctx.message.author.name}! Type `publish` to complete ' \
                                      f'this form, or `cancel` to discard all changes.'
        self.edit_embed.remove_field(0)
        self.edit_embed.remove_field(0)

        # Sink all messages to ensure user can see all information
        await self.edit_window.delete()
        # save reactions before deleting
        self.preview_window_reactions = copy.copy(self.preview_window.reactions)
        await self.preview_window.delete()

        self.edit_window = await self.ctx.send(embed=self.edit_embed)

        self.preview_window = await self.ctx.send('NEW: ', embed=self.preview_window_embed)
        for option in self.preview_ras_obj.options:
            await self.preview_window.add_reaction(option['emote'])

        old_ras_message = await self.bot.get_channel(self.ras_to_edit.channel.id).fetch_message(
            self.ras_to_edit.message.id)
        old_preview_window = await self.ctx.send('OLD: ', embed=self.ras_to_edit.message.embeds[0])
        for reaction in old_ras_message.reactions:
            await old_preview_window.add_reaction(reaction.emoji)

        try:
            retry = True
            while retry is True:

                response = await self.bot.wait_for('message', timeout=self.timeout,
                                                   check=self.message_check)

                if RGServices().word_check(response.content, 'cancel'):
                    await RGEmbeds.cancel_embed(self.edit_embed, self.edit_window, self.preview_window,
                                                title='Edit RAS :warning:',
                                                text='The edit RAS was cancelled. Your work was **not** saved')
                    await old_preview_window.delete()
                    return Status.CANCEL
                elif RGServices().word_check(response.content, 'publish'):
                    # TODO: Add change log to confirmation
                    # Apply following changes:
                    # new embed
                    await self.ras_to_edit.message.edit(embed=self.preview_window_embed)
                    # unique state
                    self.ras_to_edit.unique = self.preview_ras_obj.unique
                    # check reactions
                    self.ras_to_edit.options = self.preview_ras_obj.options

                    # Add reactions
                    for option in self.ras_to_edit.options:
                        await self.ras_to_edit.message.add_reaction(option['emote'])

                    # Remove reactions not needed
                    current_message_state = await self.ras_to_edit.channel.fetch_message(
                        self.ras_to_edit.message.id)
                    for reaction in current_message_state.reactions:
                        match = discord.utils.find(lambda o: o['emote'] == reaction.emoji,
                                                   self.ras_to_edit.options)

                        if match is None:
                            await self.ras_to_edit.message.clear_reaction(reaction.emoji)

                    # Clear roles for removed reaction
                    for role in self.roles_to_remove:
                        guild_role = discord.utils.find(lambda r: r == role,
                                                        current_message_state.guild.roles)
                        if guild_role is not None:
                            for member in guild_role.members:
                                await member.remove_roles(role)

                    # Move channel
                    if self.ras_to_edit.channel is not self.preview_ras_obj.channel:
                        new_message_ctx = await self.preview_ras_obj.channel.send(
                            embed=current_message_state.embeds[0])

                        if new_message_ctx is not None:
                            for option in self.ras_to_edit.options:
                                await new_message_ctx.add_reaction(option['emote'])
                            await self.ras_to_edit.message.delete()
                            self.ras_to_edit.channel = new_message_ctx.channel
                            self.ras_to_edit.message = new_message_ctx
                        else:
                            await self.ctx.send("Error moving RAS to another channel")

                    await old_preview_window.delete()
                    await self.preview_window.delete()

                    self.edit_embed.title = 'Edit RAS  -  :white_check_mark:'
                    self.edit_embed.description = f'CONFIRMATION'
                    self.edit_embed.colour = discord.Colour.green()
                    await self.edit_window.edit(embed=self.edit_embed)

                    # pass back message id to run validation
                    return Status.SUCCESS

        except asyncio.TimeoutError:
            await RGEmbeds.timeout_embed(self.edit_embed, self.edit_window, self.preview_window,
                                         title='Edit RAS :octagonal_sign:',
                                         text='This edit RAS session has timed out, please use the '
                                              'previous command '
                                              'to try again.')
            return Status.TIMEOUT

    def message_check(self, message):
        is_author = message.author == self.ctx.message.author
        is_correct_guild = message.guild == self.ctx.message.guild
        in_correct_channel = message.channel == self.ctx.message.channel
        return is_author and in_correct_channel and is_correct_guild
