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

client.on('message', async message =>{
    if(!message.content.includes(".tiktok.com/") || message.author.bot) return;
    
    try {
        await driver.get(message.content);
        await driver.wait(webdriver.until.elementLocated(webdriver.By.xpath('/html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video')), 100000);
        let element = await driver.findElement(webdriver.By.xpath('/html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video'));
        
        const url = await element.getAttribute('src')
        
        if (fs.existsSync('output.mp4')) {  //temp file for video output
            fs.unlinkSync('output.mp4');
        }
        const output = fs.createWriteStream('output.mp4');

        const res = await axios.get(url, {responseType: 'stream'}) //, adapter: httpAdapter
        const stream = await res.data;

        await stream.on('data', (chunk) => {     // chunk is an ArrayBuffer
            //var chunkLength = buf.length  //chunk size
            output.write(new Buffer.from(chunk));
        });
        await stream.on('end', () => {
            output.end();
            const attachment = new MessageAttachment('\output.mp4');
            message.lineReply("", attachment)
                .catch((error)=>{
                    console.log(error.name, error.message)
                    message.lineReply('Sorry. File is larger than Discord\'s 8MB Limitation.')
                });
        });        
    }
    catch(error){
        if (error.name == 'TimeoutError') {
            console.log('caught: ', error);
            console.log('name: ', error.name);
            message.lineReply("Connection Timeout: Please try again later");
          } else {
            console.log('caught: ', error);
            console.log('name: ', error.name);
            message.lineReply("idk what happened lol");
          }
    }
}    
);