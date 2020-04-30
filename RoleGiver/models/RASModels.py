import discord


# This will contain all data modeling and functions needed to manipulate a RAS session object
class RoleGiverSession:

    def __init__(self):
        # The message id of the RAS id
        self.msg = None
        # The channel the RAS is in
        self.channel = None
        # the guild the RAS is in
        self.guild = None
        # Flag for whether the RAS session is only giving one role at a time
        self.unique = False
        # [{'emote','role'}]
        # List that holds the options on the RAS
        self.options = list()
        # Current state of the RAS embed
        self.embed = None

    def print(self):
        print(
            f'[msg:{self.msg},channel:{self.channel},unique:{self.unique},options:{self.options},'
            f'embed:{self.embed.to_dict()}')

    async def add_option(self, emote, role):
        self.options.append({'emote': emote, 'role': role})

    def find_role(self, emote):
        matched_option = discord.utils.find(lambda o: o['emote'] == emote.name, self.options)
        # matched_option = None
        # for o in self.options:
        #     if o['emote'] == emote:
        #         matched_option = o

        if matched_option is not None:
            return matched_option['role']
        else:
            return None

    async def convert_from_json(self, data, bot):
        self.guild = discord.utils.get(bot.guilds, id=data['guild'])
        self.channel = discord.utils.get(self.guild.text_channels, id=data['channel'])
        self.msg = await self.channel.fetch_message(data['msg'])
        self.unique = data['unique']
        for option in data['options']:
            self.options.append({'emote': option['emote'], 'role': self.guild.get_role(option['role'])})
        self.embed = discord.Embed.from_dict(data['embed'])

    # Check what roles and reactions need to be cleaned before assigning new role
    async def clean_up_check(self, passed_user, requested_role, message):
        remove_role_list = list()
        remove_reaction_list = list()
        requested_emote = discord.utils.find(lambda r: requested_role.name == r['role'], self.options)['emote']

        # Check if there are any reactions activated that are not supposed to
        for reaction in message.reactions:
            role = discord.utils.find(lambda r: reaction.emoji == r['emote'], self.options)['role']
            if role is not None:
                # Check if user is in reaction.user list
                async for user in reaction.users():
                    if user.id is passed_user.id:
                        if reaction.emoji != requested_emote:
                            remove_reaction_list.append(reaction.emoji)
        print(f'react list: {remove_reaction_list}')
        # Check if user has roles from RAS that they are not supposed to
        for ras_role in self.options:
            result = discord.utils.find(lambda r: r.name == ras_role['role'], passed_user.roles)
            print(result)
            if result is not None:
                remove_role_list.append(result)
        # print(f'role list: {remove_role_list}')
        if len(remove_reaction_list) > 0 or len(remove_role_list) > 0:
            print([remove_reaction_list, remove_role_list])
            return {'reactions': remove_reaction_list, 'roles': remove_role_list}
        else:
            return None


# Used to hold queue items as they are processed
class QueueItem:

    def __init__(self, user, msg, ras, emote, action):
        self.user = user  # user/member object of the user
        self.message = msg  # message object of RAS
        self.ras = ras
        self.emote = emote  # which emote
        self.type = action  # add or remove reaction

    def print(self):
        print(f'{self.user}, {self.message},{self.ras} ,{self.emote}, {self.type}')
