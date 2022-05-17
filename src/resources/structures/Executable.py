from . import Permissions, Bloxlink # pylint: disable=import-error, no-name-in-module
from ..constants import OWNER, RELEASE # pylint: disable=import-error, no-name-in-module
from ..exceptions import PermissionError, Message, CancelCommand # pylint: disable=import-error, no-name-in-module
from inspect import iscoroutinefunction
import discord
import re

has_premium = Bloxlink.get_module("premium", attrs=["has_premium"])
get_guild_value = Bloxlink.get_module("cache", attrs=["get_guild_value"])
has_magic_role = Bloxlink.get_module("extras", attrs=["has_magic_role"])

flag_pattern = re.compile(r"--?(.+?)(?: ([^-]*)|$)")


class Executable:
    def __init__(self, executable):
        self.name = ""
        self.description = executable.__doc__ or "N/A"
        self.full_description = getattr(executable, "full_description", self.description)
        self.permissions = getattr(executable, "permissions", Permissions())
        self.arguments = getattr(executable, "arguments", [])
        self.category = getattr(executable, "category", "Miscellaneous")
        self.examples = getattr(executable, "examples", [])
        self.hidden = getattr(executable, "hidden", self.category == "Developer")
        self.free_to_use = getattr(executable, "free_to_use", False)
        self.addon = getattr(executable, "addon", None) # FIXME
        self.fn = getattr(executable, "__main__", None)
        self.cooldown = getattr(executable, "cooldown", 0)
        self.premium = self.permissions.premium or self.category == "Premium"
        self.developer_only = self.permissions.developer_only or self.category == "Developer" or getattr(executable, "developer_only", False) or getattr(executable, "developer", False)
        self.slash_defer = getattr(executable, "slash_defer", False)
        self.slash_ephemeral = getattr(executable, "slash_ephemeral", False)
        self.slash_args = getattr(executable, "slash_args", None)
        self.slash_guilds = getattr(executable, "slash_guilds", [])
        self.dm_allowed = getattr(executable, "dm_allowed", False)
        self.bypass_channel_perms = getattr(executable, "bypass_channel_perms", False)
        self.aliases = getattr(executable, "aliases", []) # FIXME
        self.premium_bypass_channel_perms = getattr(executable, "premium_bypass_channel_perms", False)
        self.original_executable = executable

        self.usage = []
        command_args = self.arguments

        if command_args:
            for arg in command_args:
                if arg.get("optional"):
                    if arg.get("default"):
                        self.usage.append(f'[{arg.get("name")}={arg.get("default")}]')
                    else:
                        self.usage.append(f'[{arg.get("name")}]')
                else:
                    self.usage.append(f'<{arg.get("name")}>')

        self.usage = " ".join(self.usage) if self.usage else ""

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()

    async def check_permissions(self, author, guild, channel, permissions=None, **kwargs):
        permissions = permissions or self.permissions

        if RELEASE != "LOCAL" and author.id == OWNER:
            return True

        if permissions.developer_only or self.developer_only:
            if author.id != OWNER:
                raise PermissionError("This command is reserved for the Bloxlink Developer.")

        if (kwargs.get("premium", self.premium) or permissions.premium) and not kwargs.get("free_to_use", self.free_to_use):
            prem = await has_premium(guild=guild)

            if "premium" not in prem.features:
                raise Message("This command is reserved for Bloxlink Premium subscribers!\n"
                              f"You may subscribe to Bloxlink Premium from our dashboard: {f'https://blox.link/dashboard/guilds/{guild.id}/premium' if guild else 'https://blox.link/dashboard'}", type="info")

        if permissions.function:
            if iscoroutinefunction(permissions.function):
                data = [await permissions.function(author)]
            else:
                data = [permissions.function(author)]

            if not data[0]:
                raise PermissionError("You do not have the required permissions to use this command.")

            if isinstance(data[0], tuple):
                if not data[0][0]:
                    raise PermissionError(data[0][1])

        if channel and permissions.value != 0 and not channel.permissions_for(author).is_strict_superset(permissions) and not await has_magic_role(author, guild, "Bloxlink Admin"):
            if permissions.bloxlink_updater:
                if not await has_magic_role(author, guild, "Bloxlink Updater"):
                    raise PermissionError("You do not have the required permissions to use this command.")

            raise PermissionError("You do not have the required permissions to use this command.")


class Command(Executable):
    def __init__(self, command):
        super().__init__(command)

        self.name = command.__class__.__name__[:-7].lower()
        self.subcommands = {}
        self.slash_enabled = getattr(command, "slash_enabled", False)
        self.slash_only = getattr(command, "slash_only", False)
        self.auto_complete = getattr(command, "auto_complete", False)

    async def redirect(self, CommandArgs, new_command_name, *, arguments=None, new_channel=None):
        execute_interaction_command = Bloxlink.get_module("commands", attrs=["execute_interaction_command"])

        try:
            await execute_interaction_command("commands", new_command_name, guild=CommandArgs.guild, channel=new_channel or CommandArgs.channel,
                                              user=CommandArgs.author, interaction=CommandArgs.interaction,
                                              subcommand=None, arguments=arguments, command_args=CommandArgs, forwarded=True)
        except CancelCommand:
            pass

class Application(Executable):
    def __init__(self, application):
        super().__init__(application)

        self.type = application.type
        self.name = application.name
        self.slash_enabled = True
