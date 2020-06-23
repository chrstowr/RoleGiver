import discord


class RGServices:

    @staticmethod
    def word_check(message, word):
        if message.lower().strip().startswith(word):
            return True
        else:
            return False

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

    # Parses options and returns string of options (emojis/roles) for preview window
    @staticmethod
    def option_text(options, format_type=0):
        if format_type == 0:
            if len(options) == 1:
                return options[0]
            else:
                option_text = options[0]
                count = 1
                while count < len(options):
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