import discord
from .client import MyClient
from .commands.misc import register as register_misc
from .commands.tiktok import register as register_tiktok

def create_client():
    intents = discord.Intents.default()
    intents.message_content = True
    client = MyClient(intents=intents)

    register_misc(client)
    register_tiktok(client)

    return client