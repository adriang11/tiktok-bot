from bot import create_client
from bot.config import TOKEN

client = create_client()

client.run(TOKEN)