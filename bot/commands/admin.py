import discord

def register(client):
    @client.tree.command(name = "toggle", description = "Toggle acronym troll on/off") 
    async def toggle(interaction: discord.Interaction):
        tog = await client.toggler('acronym')
        response = "Acronym Help Mode set to " + str(tog)
        await interaction.response.send_message(response)

    @client.tree.command(name = "debug", description = "Toggle debug mode on/off") 
    async def debug(interaction: discord.Interaction):
        if interaction.user.id != 474713843181027328:
            await interaction.response.send_message("You are not Adrian.", ephemeral=True)
            return

        tog = await client.toggler('debug')
        response = "Debug Mode set to " + str(tog)
        await interaction.response.send_message(response)

    @client.tree.command(name = "screencap", description = "Take screenshots along with debug info") 
    async def screencap(interaction: discord.Interaction):
        if interaction.user.id != 474713843181027328:
            await interaction.response.send_message("You are not Adrian.", ephemeral=True)
            return

        tog = await client.toggler('screencap')
        response = "Screencap Mode set to " + str(tog)
        await interaction.response.send_message(response)

    @client.tree.command(name = "clearlast", description = "Clear the last saved tiktok link") 
    async def clear_last(interaction: discord.Interaction):
        client.lastlink = ""
        await interaction.response.send_message("Last link cleared",ephemeral=True)

