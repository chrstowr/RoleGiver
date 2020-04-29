# This will contain all data modeling and functions needed to manipulate a RAS session object
class RoleGiverSession:

    def __init__(self):
        # The message id of the RAS id
        self.msg = None
        # The channel the RAS is in
        self.channel = None
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

    def add_option(self, emote, role):
        self.options.append({'emote': emote, 'role': role})

    def find_role(self, emote):
        matched_option = [r for r in self.options if r['emote'] == emote]
        if matched_option is not None:
            return matched_option['role'][0]
        else:
            return None


    # Assuming a list of roles is passed
    async def check_versus_roles(self, roles, request_role):
        matched_roles = list()
        for user_role in roles:
            for ras_role in self.options:
                if user_role.name == ras_role['role'].name and user_role.name is not request_role.name:
                    matched_roles.append(ras_role)
        if len(matched_roles) > 0:
            return matched_roles
        else:
            return None


# ENUM for what actions can be taken
class QueueAction:
    ADD = 0
    REMOVE = 1


# Used to hold queue items as they are processed
class QueueItem:

    def __init__(self, user, msg, emote, action):
        self.user = user  # user/member object of the user
        self.msg = msg  # message object of RAS
        self.emote = emote  # which emote
        self.action = action  # add or removed reaction
