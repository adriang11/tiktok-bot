const Discord = require('discord.js');
const client = new Discord.Client();

require('dotenv').config();
require('discord-reply');
const axios = require('axios');
const request = require('request');
const cheerio = require('cheerio');
const fs = require('fs');

client.login(process.env.TOKEN);

client.once('ready', () => {
    console.log('Ready to go!');
})

client.on('message', message =>{
    if(!message.content.includes(".tiktok.com/") || message.author.bot) return;

    axios.get(message.content, {responseType: 'document'})
        .then((response) => {
            console.log(response);
        })
        .catch((error) => {
            console.error(error)
        });

    message.lineReply('lol');
   
}

);