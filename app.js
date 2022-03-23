const {Client, MessageAttachment} = require('discord.js');
const client = new Client();

require('dotenv').config();
require('discord-reply');
var webdriver = require('selenium-webdriver');
const { Options, ServiceBuilder } = require('selenium-webdriver/chrome');
const axios = require('axios');
const fs = require('fs');

//*[@id="app"]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video
///html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video

let options = new Options();
options.setChromeBinaryPath(process.env.CHROME_BINARY_PATH)
options.addArguments('--headless');
//options.addArguments('--disable-gpu'); //Disables GPU hardware acceleration. If software renderer is not in place, then the GPU process won't launch.
//options.addArguments('--no-sandbox'); //Disables the sandbox. Google The sandbox is a development and test environment for developers working on Google Chrome browser-based applications. Disabling this to run on heroku
//options.addArguments('--disable-dev-shm-usage'); //This will force Chrome to use the /tmp directory instead. Fixing issue with tab crashing due to Heroku attempting to always use /dev/shm for non-executable memory.

client.login(process.env.TOKEN);

client.once('ready', () => {
    console.log('Ready to go!');
})

client.on('message', async message =>{
    if(!message.content.includes(".tiktok.com/") || message.author.bot) return;
    
    client.user.setActivity({ type: "PLAYING", name: `a game` })

    let serviceBuilder = new ServiceBuilder(process.env.CHROME_DRIVER_PATH)
    var driver = new webdriver.Builder().withCapabilities(webdriver.Capabilities.chrome()).setChromeService(serviceBuilder).build();

    try {
        await driver.get(message.content);
        await driver.wait(webdriver.until.elementLocated(webdriver.By.xpath('/html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video')), 20000);
        let element = await driver.findElement(webdriver.By.xpath('/html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video'));
        
        const url = await element.getAttribute('src')
        
        if (fs.existsSync('output.mp4')) {  //temp file for video output
            fs.unlinkSync('output.mp4');
        }
        const output = fs.createWriteStream('output.mp4');

        const res = await axios.get(url, {responseType: 'stream'}) //, adapter: httpAdapter
        const stream = await res.data;

        await stream.on('data', (chunk) => {     // chunk is an ArrayBuffer
            output.write(new Buffer.from(chunk));
        });
        await stream.on('end', () => {
            output.end();
            const attachment = new MessageAttachment('\output.mp4');
            message.lineReply("testing:", attachment)
                .catch((error)=>{
                    console.log('Caught: ', error.name, error.message)
                    message.lineReply('Sorry. File is larger than Discord\'s 8MB Limitation.')
                });
        });        
    }
    catch(error){
        if (error.name == 'TimeoutError') {
            console.log('Caught: ', error.name, error)
            message.lineReply("Connection Timeout: Please try again later");
          } else if (error.name == 'NoSuchElementError') {
            console.log('Caught: ', error.name, error)
            message.lineReply("Element Not Found On Page");
          } else {
            console.log('Caught: ', error.name, error.message)
            message.lineReply("idk what happened lol");
          }
    } finally {
        await driver.quit();
    }
}    
);