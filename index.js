const Discord = require('discord.js');

const client = new Discord.Client();

client.login('ODY4OTk0NjkzNDk5ODcxMjQy.YP3wYA.2ig2FQ41dj8LkkEJLrn2p3UtPbk');

const prefix = '!';

const fs = require('fs');

client.commands = new Discord.Collection();

const commandFiles = fs.readdirSync('./commands/').filter(file => file.endsWith('.js'));
for(const file of commandFiles){
    const command = require(`./commands/${file}`);

    client.commands.set(command.name, command);
}


client.once('ready', () => {
    console.log('Ready to go!');
})

client.on('message', message =>{
    if(!message.content.startsWith(prefix) || message.author.bot) return;

    const args = message.content.slice(prefix.length).split(/ +/);
    const command = args.shift().toLowerCase();

    if(command === 'flip'){
        client.commands.get('flip').execute(message, args);
    }

});