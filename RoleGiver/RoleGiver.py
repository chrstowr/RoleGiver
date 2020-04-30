import asyncio
import discord
import json
from collections import deque
from json import JSONDecodeError
from pathlib import Path
from RoleGiver.models.RASModels import RoleGiverSession, QueueItem


class RoleGiver:

    def __init__(self, bot):
        self.bot = bot
        self.SUCCESS = 0
        self.FAILURE = 1
        self.CANCEL = 2
        self.TIMEOUT = 4

        self.ras_sessions = list()
        # Holds queue action items to execute role adds or removals
        self.action_queue = deque()
        # Holds user id of users who were removed from a unique select RAS in order to
        # prevent on_reaction_remove event from running two times
        self.remove_tickets = deque()

    """#################################################
    create() - Routine that contains logic for the RAS (Reaction-based role Assignment System) create form.
    Helper function specific to create() will be defined under this function
    #################################################"""

    async def create(self, ctx):
        # Timeout for each step
        timeout = 320.00

        # Initialize needed variables
        ras_preview_window = None
        new_ras_session = RoleGiverSession()
        new_ras_session.embed = discord.Embed()

        # Make CREATE_RAS message embed, add needed fields
        create_ras_window = None
        create_embed = discord.Embed()
        create_embed.colour = discord.Colour.blue()
        create_embed.title = 'Create RAS'  # Never changes, title of message
        create_embed.description = 'N/A'  # Message block used by bot
        create_embed.add_field(name='tip:', value='Type `cancel` at anytime to stop', inline=False)  # tips

        # Steps in order to create new RAS message:
        """###################################
        # Ask for channel
        ###################################"""
        create_embed.title = 'Create RAS - Step 1/?'
        create_embed.description = f'Hello, {ctx.message.author.name}! Please enter the channel you would like to' \
                                   f' create an RAS in.'
        create_embed.insert_field_at(0, name='Example:', value='`#example_channel`', inline=False)
        create_ras_window = await ctx.send(embed=create_embed)
        ras_preview_window = await ctx.send('Preview:\n', embed=new_ras_session.embed)

        # Wait for response from author
        # message_check() used to check if author responded in correct channel
        def message_check(message):
            is_author = message.author == ctx.message.author
            in_correct_channel = message.channel == ctx.message.channel
            return is_author and in_correct_channel

        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=timeout, check=message_check)
                if self.word_check(response.content, 'cancel'):
                    await self.cancel_embed(create_embed, create_ras_window, ras_preview_window)
                    return self.CANCEL
                elif len(response.channel_mentions) > 0:
                    if response.channel_mentions[0] in ctx.message.guild.channels:
                        retry = False
                        new_ras_session.channel = response.channel_mentions[0]
                        new_ras_session.guild = response.guild
                else:
                    await ctx.send('Unable to verify channel')

        except asyncio.TimeoutError:
            await self.timeout_embed(create_embed, create_ras_window, ras_preview_window)
            return self.TIMEOUT

        """###################################
        # Ask for title and description 
        ###################################"""
        # Change create RAS window
        create_embed.title = 'Create RAS - Step 2/?'
        create_embed.description = f'{ctx.message.author.name}, please type out the titles and description using ' \
                                   f'this format: [title]|[description] '
        create_embed.set_field_at(0, name='Example:', value='`Test Title|This is a test description for a new RAS.`',
                                  inline=False)
        await create_ras_window.edit(embed=create_embed)

        # Wait for response from author
        # see message_check() in step 2
        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=timeout, check=message_check)
                if self.word_check(response.content, 'cancel'):
                    await self.cancel_embed(create_embed, create_ras_window, ras_preview_window)
                    return self.CANCEL
                elif self.verify_title_desc(response.content):
                    retry = False
                    items = response.content.split('|')
                    new_ras_session.embed.title = items[0].strip()
                    new_ras_session.embed.description = items[1].strip()
                    await ras_preview_window.edit(embed=new_ras_session.embed)
                else:
                    await ctx.send('Invalid format detected, please look at example above.')

        except asyncio.TimeoutError:
            await self.timeout_embed(create_embed, create_ras_window, ras_preview_window)
            return self.TIMEOUT

        """###################################
         # Ask for for emote and matching role
        ###################################"""
        # Change create RAS window
        create_embed.title = 'Create RAS - Step 3/?'
        create_embed.description = f'{ctx.message.author.name}, please list out the reaction/roles you would like to ' \
                                   f'add: \n[:the_emote:]\' \'[@role]'
        create_embed.set_field_at(0, name='Example:', value='`:warning: @spoiler_squad`',
                                  inline=False)
        create_embed.set_field_at(1, name='tip:', value='Type `cancel` at anytime to stop, `done` when you are done',
                                  inline=False)
        new_ras_session.embed.add_field(name='Current options:', value='None', inline=False)
        await create_ras_window.edit(embed=create_embed)

        # Wait for response from author
        # see message_check() in step 2
        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=timeout, check=message_check)
                if self.word_check(response.content, 'cancel'):  # Check for 'cancel'
                    await self.cancel_embed(create_embed, create_ras_window, ras_preview_window)
                    return self.CANCEL
                elif self.word_check(response.content, 'done'):  # Check for 'done'
                    retry = False

                    # Change create window tip back to basic message
                    create_embed.set_field_at(1, name='tip:',
                                              value='Type `cancel` at anytime to stop', inline=False)
                    # Remove preview of options from RAS preview
                    new_ras_session.embed.remove_field(0)
                    # Update preview window
                    await ras_preview_window.edit(embed=new_ras_session.embed)
                else:
                    # Make sure role mention is detected and get first one
                    if len(response.role_mentions) > 0:
                        items = response.content.split(' ')
                        emote = items[0]  # Get emote text
                        role = response.role_mentions[0]  # Get first role
                        # Check if role is valid
                        if role in ctx.message.guild.roles:
                            # Check if that is being inserted already exists in session
                            result = [i for i in new_ras_session.options if i['role'] == role]
                            if len(result) < 1:
                                try:
                                    # Try to add emote, if there is an exception, the emote is invalid
                                    await ras_preview_window.add_reaction(emote)
                                    # If add succeeds add to session model
                                    await new_ras_session.add_option(emote, role)
                                    # Update option list
                                    options_string = '(This will not display on final published RAS)\n'
                                    for item in new_ras_session.options:
                                        emote = item['emote']
                                        role = item['role']
                                        options_string = options_string + f'{emote} - @{role}\n'

                                    new_ras_session.embed.set_field_at(0,
                                                                       name='\nCurrent options:',
                                                                       value=options_string, inline=False)
                                    # Update option list in preview window
                                    await ras_preview_window.edit(embed=new_ras_session.embed)
                                except discord.HTTPException:
                                    await ctx.send('ERROR: Emoji is invalid')
                                except discord.DiscordException as e:
                                    print(e)
                            else:
                                await ctx.send('ERROR: An option already exists with that role')
                        else:
                            await ctx.send('ERROR: Could not validate role')
                    else:
                        await ctx.send('ERROR: Invalid format detected, please look at example above.')
        except asyncio.TimeoutError:
            await self.timeout_embed(create_embed, create_ras_window, ras_preview_window)
            return self.TIMEOUT

        """############################################
        # Ask for Unique option
        ############################################"""
        # Change create RAS window
        create_embed.title = 'Create RAS - Step 4/?'
        create_embed.description = f'{ctx.message.author.name}, Do you want the roles to be unique? (yes/no)'
        create_embed.set_field_at(0, name='Example:',
                                  value='Yes - Only one role will be assigned at a time\nNo - Multiple Roles can be '
                                        'assigned from this RAS',
                                  inline=False)
        await create_ras_window.edit(embed=create_embed)

        # Wait for response from author
        # see message_check() in step 2
        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=timeout, check=message_check)
                if self.word_check(response.content, 'cancel'):
                    await self.cancel_embed(create_embed, create_ras_window, ras_preview_window)
                    return self.CANCEL
                elif self.word_check(response.content, 'yes') or self.word_check(response.content, 'no'):
                    retry = False
                    if response.content == 'yes':
                        new_ras_session.unique = True
                        new_ras_session.embed.set_footer(text='Unique=yes')
                    else:
                        new_ras_session.unique = False
                        new_ras_session.embed.set_footer(text='Unique=no')
                    await ras_preview_window.edit(embed=new_ras_session.embed)
                else:
                    await ctx.send('Invalid format detected, please look at example above.')

        except asyncio.TimeoutError:
            await self.timeout_embed(create_embed, create_ras_window, ras_preview_window)
            return self.TIMEOUT

        """############################################
        # Color
        ############################################"""
        color = None

        """############################################
        # Publish
        ############################################"""
        # Change create RAS window
        create_embed.title = 'Create RAS - Step 6/?'
        create_embed.description = f'{ctx.message.author.name},please confirm the preview below, then type `publish` ' \
                                   f'or `cancel`'
        create_embed.clear_fields()
        await create_ras_window.edit(embed=create_embed)

        # Wait for response from author
        # see message_check() in step 2
        try:
            retry = True
            while retry is True:
                response = await self.bot.wait_for('message', timeout=timeout, check=message_check)
                if self.word_check(response.content, 'cancel'):  # Listen for 'cancel'
                    await self.cancel_embed(create_embed, create_ras_window, ras_preview_window)
                    return self.CANCEL
                elif self.word_check(response.content, 'publish'):  # Listen for 'publish'
                    retry = False
                    # Publish to requested channel
                    published_context = await new_ras_session.channel.send(embed=new_ras_session.embed)

                    # Add published message context to tracking
                    new_ras_session.msg = published_context

                    # Add reactions to publish RAS
                    for option in new_ras_session.options:
                        await published_context.add_reaction(option['emote'])

                    # Delete preview window
                    await ras_preview_window.delete()

                    # Update create RAS form with confirmation
                    create_embed.title = 'Create RAS  -  :white_check_mark:'
                    create_embed.description = f'CONFIRMATION - The new RAS has been posted in ' \
                                               f'#{new_ras_session.channel}. If you would like to edit this RAS, you can' \
                                               f' use [coming soon :)] '
                    create_embed.colour = discord.Colour.green()
                    await create_ras_window.edit(embed=create_embed)
                else:
                    await ctx.send('Invalid format detected, please look at example above.')
        except asyncio.TimeoutError:
            await self.timeout_embed(create_embed, create_ras_window, ras_preview_window)
            return self.TIMEOUT

        # Save new RAS to memory
        self.ras_sessions.append(new_ras_session)

        print(f'Newly create RAS session: {new_ras_session.print()}')

        # Save session list to disk with new addition
        self.save_sessions_to_file()

        # End routine
        return self.SUCCESS

    ####################
    # create() helpers #
    ####################

    # None

    """#################################################
       edit() - Routine that contains logic for the RAS (Reaction-based role Assignment System) edit form.
       Helper function specific to edit() will be defined under this function
    #################################################"""

    async def edit(self):
        pass

    def example_edit_helper(self):
        pass

    """#################################################
    Action functions - Handles all logic related to the action queue
    #################################################"""

    async def on_reaction_listener(self, payload):
        user = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        ras = discord.utils.find(lambda r: r.msg.id == message.id, self.ras_sessions)
        emote = payload.emoji
        action = payload.event_type
        new_queue_item = QueueItem(user, message, ras, emote, action)
        self.action_queue.append(new_queue_item)

    async def action_queue_worker(self):
        action = self.action_queue.popleft()
        requested_role = action.ras.find_role(action.emote)
        if action.type == 'REACTION_ADD':
            if action.ras.unique is True:
                # TODO: Fix awkward handling
                # Check if there are any reactions activated that are not supposed to and remove them
                for reaction in action.message.reactions:
                    # Check if user is in reaction.user list
                    async for user in reaction.users():
                        if user.id == action.user.id:
                            if reaction.emoji != action.emote.name:
                                await action.message.remove_reaction(reaction.emoji, action.user)
                                self.remove_tickets.append(action.user.id)

                # Check if user has roles from RAS that they are not supposed to
                for ras_role in action.ras.options:
                    result = discord.utils.find(lambda r: r.name == ras_role['role'], action.user.roles)
                    if result is not None:
                        await action.user.remove_roles(ras_role)

                await action.user.add_roles(requested_role)
            elif action.ras.unique is False:
                await action.user.add_roles(requested_role)
        elif action.type == 'REACTION_REMOVE':
            await action.user.remove_roles(requested_role)

    #############################
    # Action helper functions   #
    #############################
    def check_if_ras(self, message_id):
        result = [m for m in self.ras_sessions if message_id == m.msg.id]
        if len(result) > 0:
            return True
        else:
            return False

    """"################################################
    Save/Load functions for RAS session data
    ################################################"""

    def save_sessions_to_file(self):
        try:
            session_data_file = Path("RoleGiver/data.json")
            with open(session_data_file, 'w') as f:
                f.write(json.dumps(self.ras_sessions, indent=4, default=self.json_serialize_filter))
                f.close()
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')

    async def load_sessions_from_file(self):
        try:
            session_data_file = Path("RoleGiver/data.json")
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                self.ras_sessions = await self.convert_to_session_format(data)
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')

    # Helper - Take objects that are unserializable and format to serializable object
    @staticmethod
    def json_serialize_filter(obj):
        if isinstance(obj, RoleGiverSession):
            return {'msg': obj.msg.id, 'channel': obj.channel.id, 'guild': obj.guild.id, 'unique': obj.unique,
                    'options': obj.options, 'embed': obj.embed.to_dict()}
        elif isinstance(obj, discord.role.Role):
            return obj.id
        else:
            raise TypeError("Type %s not serializable" % type(obj))

    # Helper - converts the data received from JSON data file into the proper ras_session format
    async def convert_to_session_format(self, data):
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
    async def cancel_embed(embed: discord.Embed, create_ras_window: discord.Message, preview_ctx: discord.Message):
        # Template for cancel embed
        embed.colour = discord.Colour.gold()
        embed.clear_fields()
        embed.description = 'This Create RAS session has been cancelled, please use the \'c!create\' command ' \
                            'again '
        embed.title = 'Create RAS :warning:'

        # if a preview window exists close it
        if preview_ctx is not None:
            await preview_ctx.delete()

        # Replace create window with cancel embed
        await create_ras_window.edit(embed=embed)

    @staticmethod
    async def timeout_embed(embed: discord.Embed, create_ras_window: discord.Message, preview_ctx: discord.Message):
        # Template for timeout embed
        embed.colour = discord.Colour.red()
        embed.clear_fields()
        embed.description = 'This Create RAS session has timed out, please use the \'c!create\' command ' \
                            'again '
        embed.title = 'Create RAS :octagonal_sign:'

        # if a preview window exists close it
        if preview_ctx is not None:
            await preview_ctx.delete()

        # Replace create window with timeout embed
        await create_ras_window.edit(embed=embed)

    def session_count(self):
        return len(self.ras_sessions)
