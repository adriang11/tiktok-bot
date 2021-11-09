import Discord, { ReactionCollector } from 'discord.js';
import 'discord-reply';
const client = new Discord.Client();

import fetch from 'node-fetch';
import { readFile } from 'fs/promises';

const config = JSON.parse(
  await readFile(
    new URL('./config.json', import.meta.url)
  )
);

client.login(config.token);

import fs from 'fs';

client.once('ready', () => {
    console.log('Ready to go!');
})

async function getData(url) {
    let oembed = `http://www.tiktok.com/oembed/?url=${url}`;
    console.log("oembed link", oembed, '\n');
    
    let dataFromOembed = await fetch(oembed);
    let data = await dataFromOembed.json();
    if (data === undefined) {
        throw Error("No data received from oembed");
    }

    //console.log("data from oembed", data, '\n');

    return data;
}

client.on('message', message =>{
    if(!message.content.includes(".tiktok.com/") || message.author.bot) return;

    let data = getData(message.content);

    data.then(function(result) {
        console.log(result)     //console.log(data) will print: Promise { <pending> }
        message.lineReply('```json\n' + JSON.stringify(result) + '\n```');
    })


// const args = message.content.slice(prefix.length).split(/ +/);
    // const command = args.shift().toLowerCase();

    // if(command === 'flip'){
    //     client.commands.get('flip').execute(message, args);
    // }
 
},

);