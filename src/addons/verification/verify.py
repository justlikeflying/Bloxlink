from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error, no-name-in-module
import discord
from resources.exceptions import Message, UserNotVerified, Error, RobloxNotFound, BloxlinkBypass, Blacklisted, PermissionError # pylint: disable=import-error, no-name-in-module
from resources.constants import (NICKNAME_TEMPLATES, GREEN_COLOR, BROWN_COLOR, ARROW, VERIFY_URL, # pylint: disable=import-error, no-name-in-module
                                ACCOUNT_SETTINGS_URL)

get_user, get_nickname, get_roblox_id, parse_accounts, format_update_embed, guild_obligations = Bloxlink.get_module("roblox", attrs=["get_user", "get_nickname", "get_roblox_id", "parse_accounts", "format_update_embed", "guild_obligations"])
post_event = Bloxlink.get_module("utils", attrs=["post_event"])
set_guild_value = Bloxlink.get_module("cache", attrs=["set_guild_value"])



class VerifyCommand(Bloxlink.Module):
    """link your Roblox account to your Discord account and get your server roles"""

    def __init__(self):
        self.examples = ["add", "unlink", "view", "blox_link"]
        self.category = "Account"
        self.cooldown = 5
        self.dm_allowed = True
        self.slash_enabled = True
        self.slash_defer = True

    @staticmethod
    async def validate_username(message, content):
        try:
            roblox_id, username = await get_roblox_id(content)
        except RobloxNotFound:
            return None, "There was no Roblox account found with that username. Please try again."

        return username

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        guild = CommandArgs.guild
        author = CommandArgs.author
        response = CommandArgs.response

        if not guild:
            return await self.add(CommandArgs)

        if CommandArgs.command_name in ("getrole", "getroles"):
            CommandArgs.string_args = []

        try:
            old_nickname = author.display_name

            added, removed, nickname, errors, warnings, roblox_user = await guild_obligations(
                CommandArgs.author,
                join                 = True,
                guild                = guild,
                roles                = True,
                nickname             = True,
                cache                = False,
                response             = response,
                dm                   = False,
                exceptions           = ("BloxlinkBypass", "Blacklisted", "UserNotVerified", "PermissionError", "RobloxDown", "RobloxAPIError")
            )

        except BloxlinkBypass:
            raise Message("Since you have the `Bloxlink Bypass` role, I was unable to update your roles/nickname.", type="info")

        except Blacklisted as b:
            if isinstance(b.message, str):
                raise Error(f"{author.mention} has an active restriction for: `{b}`")
            else:
                raise Error(f"{author.mention} has an active restriction from Bloxlink.")

        except UserNotVerified:
            await self.add(CommandArgs)

        except PermissionError as e:
            raise Error(e.message)

        else:
            welcome_message, card, embed = await format_update_embed(
                roblox_user,
                author,
                guild=guild,
                added=added, removed=removed, errors=errors, warnings=warnings, nickname=nickname if old_nickname != nickname else None,
            )

            message = await response.send(welcome_message, files=[card.front_card_file] if card else None, view=card.view if card else None, embed=embed, mention_author=True)

            if card:
                card.response = response
                card.message = message
                card.view.message = message

            await post_event(guild, "verification", f"{author.mention} ({author.id}) has **verified** as `{roblox_user.username}`.", GREEN_COLOR)


    @Bloxlink.subcommand()
    async def add(self, CommandArgs):
        """link a new account to Bloxlink"""

        view = discord.ui.View()
        view.add_item(item=discord.ui.Button(style=discord.ButtonStyle.link, label="Verify with Bloxlink", url=VERIFY_URL, emoji="🔗"))
        view.add_item(item=discord.ui.Button(style=discord.ButtonStyle.link, label="Stuck? See a Tutorial", emoji="❔",
                                             url="https://www.youtube.com/watch?v=0SH3n8rY9Fg&list=PLz7SOP-guESE1V6ywCCLc1IQWiLURSvBE&index=2"))

        await CommandArgs.response.send("To verify with Bloxlink, click the link below.", mention_author=True, view=view)


    @Bloxlink.subcommand(permissions=Bloxlink.Permissions().build("BLOXLINK_MANAGER"))
    async def customize(self, CommandArgs):
        """customize the behavior of !verify"""

        # TODO: able to set: "forced groups"

        response = CommandArgs.response

        author = CommandArgs.author

        guild = CommandArgs.guild

        if not guild:
            return await response.send("This sub-command can only be used in a server!")

        choice = (await CommandArgs.prompt([{
            "prompt": "Which option would you like to change?\nOptions: `(welcomeMessage)`",
            "name": "choice",
            "type": "choice",
            "choices": ("welcomeMessage",)
        }]))["choice"]

        card = None

        if choice == "welcomeMessage":
            welcome_message = (await CommandArgs.prompt([{
                "prompt": f"What would you like your welcome message to be? This will be shown in `/getrole` messages.\nYou may "
                          f"use these templates: ```{NICKNAME_TEMPLATES}```",
                "name": "welcome_message",
                "formatting": False,
                "max": 1500
            }], last=True))["welcome_message"]

            await set_guild_value(guild, welcomeMessage=welcome_message)

        await post_event(guild, "configuration", f"{author.mention} ({author.id}) has **changed** the `{choice}`.", BROWN_COLOR)

        raise Message(f"Successfully saved your new `{choice}`!", type="success")


    @staticmethod
    @Bloxlink.subcommand()
    async def view(CommandArgs):
        """view your linked account(s)"""

        author = CommandArgs.author
        response = CommandArgs.response

        try:
            primary_account, accounts, _ = await get_user("username", user=author, everything=False, basic_details=True)
        except UserNotVerified:
            raise Message("You have no accounts linked to Bloxlink!", type="info")
        else:
            accounts = list(accounts)

            parsed_accounts = await parse_accounts(accounts, reverse_search=True)
            parsed_accounts_str = []
            primary_account_str = "No primary account set"

            for roblox_username, roblox_data in parsed_accounts.items():
                if roblox_data[1]:
                    username_str = []

                    for discord_account in roblox_data[1]:
                        username_str.append(f"{discord_account} ({discord_account.id})")

                    username_str = ", ".join(username_str)

                    if primary_account and roblox_username == primary_account.username:
                        primary_account_str = f"**{roblox_username}** {ARROW} {username_str}"
                    else:
                        parsed_accounts_str.append(f"**{roblox_username}** {ARROW} {username_str}")

                else:
                    parsed_accounts_str.append(f"**{roblox_username}**")

            parsed_accounts_str = "\n".join(parsed_accounts_str)


            embed = discord.Embed(title="Linked Roblox Accounts")
            embed.add_field(name="Primary Account", value=primary_account_str)
            embed.add_field(name="Secondary Accounts", value=parsed_accounts_str or "No secondary account saved")
            embed.set_author(name=author, icon_url=author.avatar.url if author.avatar else None)

            await response.send(embed=embed, dm=True, strict_post=True)

    @staticmethod
    @Bloxlink.subcommand()
    async def unlink(CommandArgs):
        """unlink an account from Bloxlink"""

        if CommandArgs.guild:
            await CommandArgs.response.reply(f"to manage your accounts, please visit our website: <{ACCOUNT_SETTINGS_URL}>", mention_author=True)
        else:
            await CommandArgs.response.send(f"To manage your accounts, please visit our website: <{ACCOUNT_SETTINGS_URL}>", mention_author=True)
