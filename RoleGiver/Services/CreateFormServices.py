import asyncio

import discord

from RoleGiver.Models.RASModels import RoleGiverSession
from RoleGiver.Services.GeneralServices import RGServices
from RoleGiver.Views.DiscordEmbeds import RGEmbeds

class CreateForm:

    def __init__(self, ctx, bot, ras_sessions):
        self.ctx = ctx
        self.bot = bot
        self.ras_sessions = ras_sessions
        self.SUCCESS = 0
        self.FAILURE = 1
        self.CANCEL = 2
        self.TIMEOUT = 4
        self.timeout = 320.00

        # Variables for the new RAS session
        self.ras_preview_window = None
        self.new_ras_session = RoleGiverSession()
        self.new_ras_session_embed = discord.Embed()
        self.new_ras_session_embed.colour = discord.Colour.default()

        # CREATE_RAS message embed, add needed fields
        self.create_ras_window = None
        self.create_embed = discord.Embed()
        self.create_embed.colour = discord.Colour.blue()
        self.create_embed.title = 'Create RAS'  # Never changes, title of message
        self.create_embed.description = 'N/A'  # Message block used by bot
        self.create_embed.add_field(name='tip:', value='Type `cancel` at anytime to stop', inline=False)  # tips

        # Max steps in form
        self.max_steps = 0
        # Track steps
        self.current_step = 1

        self.form_queue = list()

    def add_step(self, func):
        self.form_queue.append(func)
        self.max_steps = self.max_steps + 1

    async def run(self):
        for func in self.form_queue:
            result = await func()
            if result is not self.SUCCESS:
                return result

        return self.SUCCESS

    async def get_channel(self):
        """###################################
        # Ask for channel/guild
        ###################################"""
        self.create_embed.title = f'Create RAS - Step {self.current_step}/{self.max_steps}'
        self.create_embed.description = f'Hello, {self.ctx.message.author.name}! Please enter the channel you would like to' \
                                        f' create an RAS in.'
        self.create_embed.insert_field_at(0, name='Example:', value='`#example_channel`', inline=False)
        self.create_ras_window = await self.ctx.send(embed=self.create_embed)
        self.ras_preview_window = await self.ctx.send('Preview:\n', embed=self.new_ras_session_embed)

        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=self.timeout, check=self.message_check)
                if RGServices.word_check(response.content, 'cancel'):
                    await RGEmbeds.cancel_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                            title='Create RAS :warning:',
                                            text='This create RAS sessions was cancelled, use the create command'
                                                 ' again to start another session.')
                    return self.CANCEL
                elif len(response.channel_mentions) > 0:
                    if response.channel_mentions[0] in self.ctx.message.guild.channels:
                        channel = self.bot.get_channel(response.channel_mentions[0].id)
                        if channel is not None:
                            self.new_ras_session.channel = channel
                            self.new_ras_session.guild = channel.guild
                            retry = False
                            self.current_step = self.current_step + 1
                            return self.SUCCESS
                        else:
                            await self.ctx.send('Unable to verify channel')
                else:
                    await self.ctx.send('Unable to verify channel')

        except asyncio.TimeoutError:

            await RGEmbeds.timeout_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                     title='Create RAS :octagonal_sign:',
                                     text='This Create RAS session has timed out, please use the \'c!create\' command '
                                          'again ')
            return self.TIMEOUT

    async def get_title_desc(self):
        """###################################
        # Ask for title and description
        ###################################"""

        # Change create RAS window

        self.create_embed.title = f'Create RAS - Step {self.current_step}/{self.max_steps}'
        self.create_embed.description = f'{self.ctx.message.author.name}, please type out the titles and description using ' \
                                        f'this format: [title]|[description] '
        self.create_embed.set_field_at(0, name='Example:',
                                       value='`Test Title|This is a test description for a new RAS.`',
                                       inline=False)
        await self.create_ras_window.edit(embed=self.create_embed)

        # Wait for response from author
        # see message_check() in step 2
        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=self.timeout, check=self.message_check)
                if RGServices().word_check(response.content, 'cancel'):
                    await RGEmbeds.cancel_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                            title='Create RAS :warning:',
                                            text='This create RAS sessions was cancelled, use the create command'
                                                 ' again to start another session.')
                    return self.CANCEL
                elif RGServices().verify_title_desc(response.content):
                    retry = False
                    items = response.content.split('|')
                    self.new_ras_session_embed.title = items[0].strip()
                    self.new_ras_session_embed.description = items[1].strip()
                    await self.ras_preview_window.edit(embed=self.new_ras_session_embed)
                    return self.SUCCESS
                else:
                    await self.ctx.send('Invalid format detected, please look at example above.')

        except asyncio.TimeoutError:
            await RGEmbeds.timeout_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                     title='Create RAS :octagonal_sign:',
                                     text='This Create RAS session has timed out, please use the \'c!create\' command '
                                          'again ')
            return self.TIMEOUT

    async def get_emote_role(self):
        """###################################
        # Ask for for emote and matching role
        ###################################"""
        # Change create RAS window
        self.create_embed.title = f'Create RAS - Step {self.current_step}/{self.max_steps}'
        self.create_embed.description = f'{self.ctx.message.author.name}, please list out the reaction/roles you would like to ' \
                                        f'add: \n[:the_emote:]\' \'[@role]. To delete a line type \'del [int]\''
        self.create_embed.set_field_at(0, name='Example:', value='`:warning: @spoiler_squad`\n`del 1`',
                                       inline=False)
        self.create_embed.set_field_at(1, name='tip:',
                                       value='Type `cancel` at anytime to stop, `done` when you are done',
                                       inline=False)
        self.new_ras_session_embed.add_field(name='Current options:', value='None', inline=False)
        await self.create_ras_window.edit(embed=self.create_embed)

        # Wait for response from author
        # see message_check() in step 2
        try:
            retry = True
            options_strings = ['(This will not display on final published RAS)\n']
            while retry is True:
                response = await self.bot.wait_for('message', timeout=self.timeout, check=self.message_check)
                if RGServices().word_check(response.content, 'cancel'):  # Check for 'cancel'
                    await RGEmbeds.cancel_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                            title='Create RAS :warning:',
                                            text='This create RAS sessions was cancelled, use the create command'
                                                 ' again to start another session.')
                    return self.CANCEL
                elif RGServices().word_check(response.content, 'del'):
                    # Get first argument after delete
                    arg = response.content.strip(' ').split(' ')
                    if len(arg) > 1:
                        arg = arg[1].strip(' ')
                        # Check if is int
                        if RGServices().is_int(arg) is True:
                            delete_option = int(arg)
                            if 0 < delete_option < len(options_strings):
                                # Remove from option list
                                option_to_remove = options_strings.pop(delete_option)
                                # Remove from RAS
                                await self.new_ras_session.remove_option(option_to_remove[0])
                                # Remove reaction
                                await self.ras_preview_window.remove_reaction(option_to_remove[0], self.bot.user)

                                # update preview window
                                option_text = RGServices().option_text(options_strings)
                                self.new_ras_session_embed.set_field_at(0,
                                                                        name='\nCurrent options:',
                                                                        value=option_text, inline=False)
                                # Update option list in preview window
                                await self.ras_preview_window.edit(embed=self.new_ras_session_embed)

                elif RGServices().word_check(response.content, 'done'):  # Check for 'done'
                    retry = False

                    # Change create window tip back to basic message
                    self.create_embed.set_field_at(1, name='tip:',
                                                   value='Type `cancel` at anytime to stop', inline=False)
                    # Remove preview of options from RAS preview
                    self.new_ras_session_embed.remove_field(0)
                    # Update preview window
                    await self.ras_preview_window.edit(embed=self.new_ras_session_embed)
                    return self.SUCCESS
                else:
                    # Make sure role mention is detected and get first one
                    if len(response.role_mentions) > 0:
                        items = response.content.split(' ')
                        emote = items[0]  # Get emote text
                        role = response.role_mentions[0]  # Get first role
                        # Check if role is valid
                        if role in self.ctx.message.guild.roles:
                            # Check if that is being inserted already exists in session
                            result = [i for i in self.new_ras_session.options if i['role'] == role]
                            if len(result) < 1:
                                try:
                                    # Try to add emote, if there is an exception, the emote is invalid
                                    await self.ras_preview_window.add_reaction(emote)
                                    # If add reaction succeeds add to session model
                                    await self.new_ras_session.add_option(emote, role)
                                    # Update option list
                                    options_strings.append([emote, role])
                                    option_text = RGServices.option_text(options_strings)
                                    self.new_ras_session_embed.set_field_at(0,
                                                                            name='\nCurrent options:',
                                                                            value=option_text, inline=False)
                                    # Update option list in preview window
                                    await self.ras_preview_window.edit(embed=self.new_ras_session_embed)
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
                            await self.ras_preview_window.add_reaction(emote)
                            # If add reaction succeeds add to session model
                            await self.new_ras_session.add_option(emote, None)
                            # Update option list
                            options_strings.append([emote, 'N/A'])
                            option_text = RGServices().option_text(options_strings)
                            self.new_ras_session_embed.set_field_at(0,
                                                                    name='\nCurrent options:',
                                                                    value=option_text, inline=False)
                            # Update option list in preview window
                            await self.ras_preview_window.edit(embed=self.new_ras_session_embed)
                        except discord.HTTPException:
                            await self.ctx.send('ERROR: Emoji is invalid')
                        except discord.DiscordException as e:
                            print(e)
                    # else:
                    #     await self.ctx.send('ERROR: Invalid format detected, please look at example above.')
        except asyncio.TimeoutError:
            await RGEmbeds.timeout_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                     title='Create RAS :octagonal_sign:',
                                     text='This Create RAS session has timed out, please use the \'c!create\' command '
                                          'again ')
            return self.TIMEOUT

    async def get_unique_flag(self):
        """############################################
        # Ask for Unique option
        ############################################"""
        # Change create RAS window
        self.create_embed.title = f'Create RAS - Step {self.current_step}/{self.max_steps}'
        self.create_embed.description = f'{self.ctx.message.author.name}, Do you want the roles to be unique? (yes/no)'
        self.create_embed.set_field_at(0, name='Example:',
                                       value='Yes - Only one role will be assigned at a time\nNo - Multiple Roles can be '
                                             'assigned from this RAS',
                                       inline=False)
        await self.create_ras_window.edit(embed=self.create_embed)

        # Wait for response from author
        # see message_check() in step 2
        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=self.timeout, check=self.message_check)
                if RGServices().word_check(response.content, 'cancel'):
                    await RGEmbeds.cancel_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                            title='Create RAS :warning:',
                                            text='This create RAS sessions was cancelled, use the create command'
                                                 ' again to start another session.')
                    return self.CANCEL
                elif RGServices().word_check(response.content, 'yes') or RGServices().word_check(response.content, 'no'):
                    retry = False
                    if RGServices().word_check(response.content, 'yes'):
                        self.new_ras_session.unique = True
                        self.new_ras_session_embed.set_footer(text=f'Unique={True}')
                    elif RGServices().word_check(response.content, 'no'):
                        self.new_ras_session.unique = False
                        self.new_ras_session_embed.set_footer(text=f'Unique={False}')
                    await self.ras_preview_window.edit(embed=self.new_ras_session_embed)
                    return self.SUCCESS
                else:
                    await self.ctx.send('Invalid format detected, please look at example above.')

        except asyncio.TimeoutError:
            await RGEmbeds.timeout_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                     title='Create RAS :octagonal_sign:',
                                     text='This Create RAS session has timed out, please use the \'c!create\' command '
                                          'again ')
            return self.TIMEOUT

    async def get_color(self):
        """############################################
        # Color
        ############################################"""
        # Change create RAS window
        self.create_embed.title = f'Create RAS - Step {self.current_step}/{self.max_steps}'
        self.create_embed.description = f'{self.ctx.message.author.name}, please choose the color you want to associate with ' \
                                        f'this RAS in this format `[0-255],[0-255],[0-255]` See tip for example.'
        self.create_embed.set_field_at(0, name='Example:', value='`255,255,255`',
                                       inline=False)
        self.create_embed.set_field_at(1, name='tip:',
                                       value='Type `cancel` at anytime to stop, `done` when you are done',
                                       inline=False)
        current_color = self.new_ras_session_embed.colour
        self.new_ras_session_embed.add_field(name='Current color:',
                                             value=f'{current_color.to_rgb()}', inline=False)

        await self.create_ras_window.edit(embed=self.create_embed)
        await self.ras_preview_window.edit(embed=self.new_ras_session_embed)

        # Wait for response from author
        # see message_check() in step 2
        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=self.timeout, check=self.message_check)
                if RGServices().word_check(response.content, 'cancel'):  # Check for 'cancel'
                    await RGEmbeds.cancel_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                            title='Create RAS :warning:',
                                            text='This create RAS sessions was cancelled, use the create command'
                                                 ' again to start another session.')
                    return self.CANCEL
                elif RGServices().word_check(response.content, 'done'):  # Check for 'done'
                    retry = False

                    # Change create window tip back to basic message
                    self.create_embed.set_field_at(1, name='tip:',
                                                   value='Type `cancel` at anytime to stop', inline=False)
                    # Remove preview of options from RAS preview
                    self.new_ras_session_embed.remove_field(0)
                    # Update preview window
                    await self.ras_preview_window.edit(embed=self.new_ras_session_embed)
                    return self.SUCCESS
                else:
                    new_color = RGServices().color_atlas(response)
                    if new_color is not None:
                        self.new_ras_session_embed.colour = new_color

                        self.new_ras_session_embed.set_field_at(0,
                                                                name='\nCurrent color:',
                                                                value=new_color.to_rgb(), inline=False)
                        await self.ras_preview_window.edit(embed=self.new_ras_session_embed)

        except asyncio.TimeoutError:
            await RGEmbeds.timeout_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                     title='Create RAS :octagonal_sign:',
                                     text='This Create RAS session has timed out, please use the \'c!create\' command '
                                          'again ')
            return self.TIMEOUT

    async def publish(self):
        """############################################
        # Publish
        ############################################"""
        # Change create RAS window
        self.create_embed.title = f'Create RAS - Step {self.current_step}/{self.max_steps}'
        self.create_embed.description = f'{self.ctx.message.author.name},please confirm the preview below, then type `publish` ' \
                                        f'or `cancel`'
        self.create_embed.clear_fields()
        await self.create_ras_window.edit(embed=self.create_embed)

        # Wait for response from author
        # see message_check() in step 2
        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=self.timeout, check=self.message_check)
                if RGServices().word_check(response.content, 'cancel'):  # Listen for 'cancel'
                    await RGEmbeds.cancel_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                            title='Create RAS :warning:',
                                            text='This create RAS sessions was cancelled, use the create command'
                                                 ' again to start another session.')
                    return self.CANCEL
                elif RGServices().word_check(response.content, 'publish'):  # Listen for 'publish'
                    retry = False
                    # Publish to requested channel
                    published_context = await self.new_ras_session.channel.send(embed=self.new_ras_session_embed)

                    # Add published message context to tracking
                    self.new_ras_session.message = published_context

                    # Add reactions to publish RAS
                    for option in self.new_ras_session.options:
                        await published_context.add_reaction(option['emote'])

                    # Delete preview window
                    await self.ras_preview_window.delete()
                    # TODO: Add list of what options are in confirmation
                    # Update create RAS form with confirmation
                    self.create_embed.title = 'Create RAS  -  :white_check_mark:'
                    self.create_embed.description = f'CONFIRMATION - The new RAS has been posted in ' \
                                                    f'#{self.new_ras_session.channel}. If you would like to edit this RAS, you can' \
                                                    f' use [coming soon :)] '
                    self.create_embed.colour = discord.Colour.green()
                    await self.create_ras_window.edit(embed=self.create_embed)
                else:
                    await self.ctx.send('Invalid format detected, please look at example above.')
        except asyncio.TimeoutError:
            await RGEmbeds.timeout_embed(self.create_embed, self.create_ras_window, self.ras_preview_window,
                                     title='Create RAS :octagonal_sign:',
                                     text='This Create RAS session has timed out, please use the \'c!create\' command '
                                          'again ')
            return self.TIMEOUT

        # Save new RAS to memory
        self.ras_sessions.append(self.new_ras_session)

        # End routine
        return self.SUCCESS

    def message_check(self, message):
        is_author = message.author == self.ctx.message.author
        in_correct_channel = message.channel == self.ctx.message.channel
        return is_author and in_correct_channel
