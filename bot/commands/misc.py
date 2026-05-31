import discord
import random
from discord import Member
from bot.data.statics import friends
from toolz import get_in
from typing import Optional

def register(client):
    @client.tree.command(name = "test", description = "Says 'yo'. Nothing else") 
    async def test_command(interaction: discord.Interaction):
        await interaction.response.send_message("yo")

    @client.tree.command(name = "fortune", description = "Tells you a special fortune you need to hear") #using to determine version deployed on heroku
    async def fortune(interaction: discord.Interaction):
        await interaction.response.send_message("Everyone is alive. Very few are living.")

    @client.tree.command(name = "coinflip", description = "flips a coin") 
    async def coinflip(interaction: discord.Interaction):
        flip = random.randint(0,1)
        if(flip == 0):
            await interaction.response.send_message("Heads!")
        else:
            await interaction.response.send_message("Tails!")

    @client.tree.command(name = "blame", description = "Tells you exactly who to blame for anything") 
    async def blame(interaction: discord.Interaction):
        friend = random.choice(friends)
        await client.log(f'Blame game played: {friend}\n', interaction)
        await interaction.response.send_message("This is clearly " + friend.title() + "\'s fault")

    @client.tree.command(name = "wisdom", description = "Receive a random wisdom from Pascal the Sea Otter") 
    async def daily_wisdom(interaction: discord.Interaction):
        fd = open("wisdom.txt", "r", encoding='utf-8')
        lines = fd.readlines()
        wisdom = random.choice(lines)
        fd.close()
        await client.log(f'Wisdom sent: {wisdom}\n', interaction)
        await interaction.response.send_message(wisdom)

    @client.tree.command(name = "mywisdom", description = "Receive a random wisdom from Adrian the Chango") 
    async def adrians_wisdom(interaction: discord.Interaction):
        wisdom = random.choice(client.wisdoms)
        await client.log(f'Wisdom sent: {wisdom}\n', interaction)
        await interaction.response.send_message(wisdom)

    @client.tree.command(name = "divswisdom", description = "Receive a random wisdom from Divanni the Gomez") 
    async def divs_wisdom3(interaction: discord.Interaction):
        wisdom = random.choice(client.divswisdoms)
        await client.log(f'Wisdom sent: {wisdom}\n', interaction)
        await interaction.response.send_message(wisdom)

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

    @client.tree.command(name = "clearlast", description = "Clear the last saved tiktok link") 
    async def clear_last(interaction: discord.Interaction):
        client.lastlink = ""
        await interaction.response.send_message("Last link cleared",ephemeral=True)

    @client.tree.command(name = "poll", description = "Creates a poll") 
    async def poll(interaction: discord.Interaction, message: str, choice1: str, choice2: str, choice3: Optional[str], choice4: Optional[str], choice5: Optional[str], choice6: Optional[str], choice7: Optional[str], choice8: Optional[str], choice9: Optional[str], choice10: Optional[str]):
        
        
        emojis = ['1️⃣','2️⃣', '3️⃣','4️⃣', '5️⃣', '6️⃣','7️⃣','8️⃣','9️⃣','🔟']
        options = [choice1, choice2, choice3, choice4, choice5, choice6, choice7,choice8,choice9,choice10]
        clean = False
        x = -1

        while(not clean):
            if (options[x] is None):
                options.pop()
            else:
                clean = True

        correctsize = range(len(options))

        for i in correctsize:
            options[i] = f"{emojis[i]} {options[i]} \n"
        options = '\n'.join(options)

        embed = discord.Embed(title=message, description=options, color=0x13a6f0)
        
        footer_text = 'Poll created by ' + interaction.user.display_name
        embed.set_footer(text=footer_text)
        
        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()

        for i in correctsize:
            await sent.add_reaction(emojis[i])

    @client.tree.command(name="test_birthday", description="Display all registered birthday(s) in the server")
    async def test_birthday(interaction: discord.Interaction, user: discord.User = None):
        await client.log(f'[DEBUG TRACE] test birthday called\n', interaction)

        members = {"1":{"Name":"rachelle","Birthday":"1/3"},
                "2":{"Name":"ruth","Birthday":"1/18"},
                "3":{"Name":"nik","Birthday":"4/24"},
                "4":{"Name":"josh","Birthday":"7/18"},
                "5":{"Name":"jasper","Birthday":"7/19"},
                "6":{"Name":"adrian","Birthday":"11/19"},
                "7":{"Name":"hari","Birthday":"11/22"},
                "8":{"Name":"sadiya","Birthday":"11/22"},
                "9":{"Name":"Fermi","Birthday":"12/6"},
                "10":{"Name":"Neha","Birthday":"12/19"}
                }

        if user is None:
            date_format = "%m/%d"
            
            sorted_birthdays = members

            items = list(members.items())

            mid = len(items) // 2

            await client.log(f'[DEBUG TRACE] midpoint is {mid}\n', interaction)
            
            # If odd move midpoint over by 1
            if len(items) % 2:
                mid+=1
                await client.log(f'[DEBUG TRACE] list is odd: {mid}\n', interaction)

            first_half = items[:mid]
            second_half = items[mid:]

            interleaved = []
            for a, b in zip(first_half, second_half):
                interleaved.extend([a, b])

            # If odd length, add the leftover from second_half
            if len(first_half) > len(second_half):
                interleaved.append(first_half[-1])

            # Rebuild dictionary in new order
            freaky_style = dict(interleaved)

            columns = 0
            newline=False

            embed = discord.Embed(title=f"Degen Birthdays - {len(sorted_birthdays)} (Please memorize the entire list)", color=discord.Color.blue())
            for member_id, member_data in freaky_style.items():
                if newline: 
                    embed.add_field(name='\t',value='\t')
                    newline=False

                name = member_data["Name"]
                birthday = member_data["Birthday"]
                embed.add_field(name=name, value=birthday, inline=True)
                columns+=1

                if columns==2:
                    columns=0
                    newline=True
            
            embed.add_field(name='\t',value='\t')


            await interaction.response.send_message(embed=embed)
            
        else:
            user_id = str(user.id)
            if user_id in members:
                birthday = members[user_id]["Birthday"]
                color = members[user_id]["Color"]
                pfp = user.display_avatar
                embed = discord.Embed(title=f"{user.display_name}'s Birthday", color=discord.Color.from_str(color))
                embed.description = f"{birthday}"
                embed.set_thumbnail(url=pfp)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("This user has not registered!", ephemeral=True)
                return

    @client.tree.command(name = "goodluck", description = "Says 'Good Luck' to you. Nothing else") 
    async def good_luck(interaction: discord.Interaction, user: Optional[Member] = None):
        await interaction.response.send_message("Watch how I do this.",ephemeral=True)
        if user:
            await interaction.channel.send(f"Good Luck! {user.mention}")
        else:
            await interaction.channel.send(f"Good Luck! {interaction.user.mention}")
