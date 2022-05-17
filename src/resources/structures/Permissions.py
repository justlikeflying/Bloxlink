import discord


class Permissions(discord.Permissions):
    """Contains permission attributes for commands"""

    def __init__(self, function=None, bloxlink_updater=False, bloxlink_admin=False, premium=False, **kwargs):
        self.function = function
        self.developer_only = False
        self.premium = premium
        self.bloxlink_updater = bloxlink_updater
        self.bloxlink_admin = bloxlink_admin


        self.allow_bypass = False

        super().__init__(**kwargs)
