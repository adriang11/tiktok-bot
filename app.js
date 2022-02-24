const Discord = require('discord.js');
const client = new Discord.Client();

require('dotenv').config();
require('discord-reply');
const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');

client.login(process.env.TOKEN);

client.once('ready', () => {
    console.log('Ready to go!');
})

//my user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36

var config = {headers: {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36'}};

client.on('message', message =>{
    if(!message.content.includes(".tiktok.com/") || message.author.bot) return;

    axios.get(message.content)
        .then((response) => {  
            console.log(response);
        })
        .catch((error) => {
            console.error(error)
        });

    message.lineReply('lol');   
}
);