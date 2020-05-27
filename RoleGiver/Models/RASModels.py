import discord
from time import perf_counter


# This will contain all data modeling and functions needed to manipulate a RAS session object
class RoleGiverSession:

    def __init__(self):
        # The message id of the RAS in
        self.message = None
        # The channel the RAS is in
        self.channel = None
        # the guild the RAS is in
        self.guild = None
        # Flag for whether the RAS session is only giving one role at a time
        self.unique = False
        # emote = the emoji, users = the list of users who has reacted to this msg (CACHED FOR FASTER ACCESS)
        # [{'emote':x,'role':y,'users':z}]
        # List that holds the options on the RAS
        self.options = list()

    def print(self):
        # Todo: Convert user list to names for easier reading
        return f'[message:{self.message},channel:{self.channel},unique:{self.unique},options:{self.options}]'

    async def add_option(self, emote, role):
        self.options.append({'emote': emote, 'role': role, 'users': list()})

    async def remove_option(self, emote):

        cleaned_emote = None

        if type(emote) is str:
            cleaned_emote = emote
        else:
            cleaned_emote = emote.name

        option_to_remove = discord.utils.find(lambda o: o['emote'] == cleaned_emote, self.options)
        print(option_to_remove)
        self.options.remove(option_to_remove)

    # Returns list of roles associated with this RAS
    def role_list(self):
        return [r['role'] for r in self.options if r is not None]

    def find_role(self, emote):
        cleaned_emote = None

        if type(emote) is str:
            cleaned_emote = emote
        else:
            cleaned_emote = emote.name

        matched_option = discord.utils.find(lambda o: o['emote'] == cleaned_emote, self.options)

        if matched_option is not None:
            return matched_option['role']
        else:
            return None

    async def cache_user(self, user, role, emote):
        # Search by emote
        if role is None:
            option = discord.utils.find(lambda o: o['emote'] == emote.name, self.options)
        # Search by role
        else:
            option = discord.utils.find(lambda o: o['role'] == role, self.options)

        if option is not None:
            if user not in option['users']:
                option['users'].append(user)

    def release_from_cache(self, user, role, emote):
        # Search by emote
        if role is None:
            option = discord.utils.find(lambda o: o['emote'] == emote, self.options)
        # Search by role
        else:
            option = discord.utils.find(lambda o: o['role'] == role, self.options)

        if user in option['users']:
            option['users'].remove(user)

    def cache_user_with_role(self, user, role):
        option = discord.utils.find(lambda o: o['role'] == role, self.options)
        if user not in option['users']:
            option['users'].append(user)

    def remove_user_from_cache_with_role(self, user, role):
        option = discord.utils.find(lambda o: o['role'] == role, self.options)
        if user in option['users']:
            option['users'].remove(user)

    async def convert_from_json(self, data, bot):
        self.guild = discord.utils.get(bot.guilds, id=data['guild'])
        self.channel = discord.utils.get(self.guild.text_channels, id=data['channel'])
        self.message = await self.channel.fetch_message(data['msg'])
        self.unique = data['unique']
        for option in data['options']:
            reaction = discord.utils.find(lambda r: r.emoji == option['emote'], self.message.reactions)
            self.options.append(
                {'emote': option['emote'], 'role': self.guild.get_role(option['role']),
                 'users': await reaction.users().flatten()})


# Used to hold queue items as they are processed
class QueueItem:

    def __init__(self, user, msg, ras, emote, action):
        self.user = user  # user/member object of the user
        self.message_path = msg  # message object of RAS
        self.ras = ras
        self.emote = emote  # which emote
        self.type = action  # add or remove reaction

    def print(self):
        print(f'{self.user}, {self.message_path},{self.ras} ,{self.emote}, {self.type}')
