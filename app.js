const Discord = require('discord.js');
const client = new Discord.Client();

require('dotenv').config();
require('discord-reply');
const request = require('request');
const cheerio = require('cheerio');
const fs = require('fs');

client.login(process.env.TOKEN);

client.once('ready', () => {
    console.log('Ready to go!');
})

client.on('message', message =>{
    if(!message.content.includes(".tiktok.com/") || message.author.bot) return;

    //test link: 'http://google.com/doodle.png'

    request(message.content, function(error, response, html){
        console.error('error:', error);
        console.log('statusCode: ', response && response.statusCode);
        console.log('html: ', html);
    });

    message.lineReply('lol');
   
},

);