import asyncio
import discord
import json
from json import JSONDecodeError
from pathlib import Path
from RoleGiver.models.RASModels import RoleGiverSession, QueueItem, QueueAction


class RoleGiver:

    def __init__(self, bot):
        self.bot = bot
        self.SUCCESS = 0
        self.FAILURE = 1
        self.CANCEL = 2
        self.TIMEOUT = 4

        self.ras_sessions = list()
        # self.action_queue = deque()

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
                            result = [i for i in new_ras_session.options if i['role'] == role]
                            if len(result) < 1:
                                try:
                                    # Try to add emote, if there is an exception, the emote is invalid
                                    await ras_preview_window.add_reaction(emote)
                                    # If add succeeds add to session model
                                    new_ras_session.add_option(emote, role)
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
                    self.ras_sessions.append(new_ras_session)
                    print(f'1: {new_ras_session.print()}')
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

    async def add_role(self, reaction, user):
        ras = [s for s in self.ras_sessions if reaction.message.id == s.msg.id][0]
        role = discord.utils.find(lambda r: r == ras.find_role(reaction.emoji), reaction.message.guild.roles)

        if role is not None:
            # If unique is false, that means that the RAS can hand out multiple roles
            # If unique is true, that means that the RAS can hand out ONE role at a time
            if ras.unique is False:
                await user.add_roles(role)
            elif ras.unique is True:
                # Need to check if the user has another role from RAS
                result = await ras.check_versus_roles(user.roles, role)
                # If yes, remove them
                if result is not None:
                    for matching_option in result:
                        await reaction.message.remove_reaction(matching_option['emote'], user)

                await user.add_roles(role)

    async def remove_role(self, reaction, user):
        ras = [s for s in self.ras_sessions if reaction.message.id == s.msg.id][0]
        role = discord.utils.find(lambda r: r == ras.find_role(reaction.emoji), reaction.message.guild.roles)
        await user.remove_roles(role)

    #############################
    # Action helper functions   #
    #############################
    def check_for_ras(self, message: discord.Message):
        result = [m for m in self.ras_sessions if message.id == m.msg.id]
        if len(result) > 0:
            return True
        else:
            return False

    """"################################################
    Save/Load functions for RAS session data
    ################################################"""

    def save_sessions_to_file(self):
        try:
            duel_data_file = Path("RoleGiver/data.json")
            with open(duel_data_file, 'w') as f:
                f.write(json.dumps(self.ras_sessions, indent=4, default=self.json_serialize_filter))
                f.close()
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')

    def load_sessions_from_file(self):
        pass

    # Helper - Take objects that are unserializable and format to serializable object
    @staticmethod
    def json_serialize_filter(obj):
        if isinstance(obj, RoleGiverSession):
            return {'msg': obj.msg.id, 'channel': obj.channel.id, 'unique': obj.unique,
                    'options': obj.options, 'embed': obj.embed.to_dict()}
        elif isinstance(obj, discord.role.Role):
            return obj.name
        else:
            raise TypeError("Type %s not serializable" % type(obj))

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
