const {Client, MessageAttachment} = require('discord.js');
const client = new Client();

require('dotenv').config();
require('discord-reply');
var webdriver = require('selenium-webdriver');
var driver = new webdriver.Builder().withCapabilities(webdriver.Capabilities.chrome()).build();
const axios = require('axios');
const fs = require('fs');

//*[@id="app"]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video
///html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video


client.login(process.env.TOKEN);

client.once('ready', () => {
    console.log('Ready to go!');
})

client.on('message', message =>{
    if(!message.content.includes(".tiktok.com/") || message.author.bot) return;
    
    driver.get(message.content);
    driver.wait(webdriver.until.elementLocated(webdriver.By.xpath('/html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video')), 10000);
    let element = driver.findElement(webdriver.By.xpath('/html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video'));
    
    element.getAttribute('src')
        .then(function(url){
            //const attachment = new MessageAttachment(url)

            message.lineReply(url); 
        });
}
);