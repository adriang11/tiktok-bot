const {Client, MessageAttachment} = require('discord.js');
const client = new Client();

require('dotenv').config();
require('discord-reply');
var webdriver = require('selenium-webdriver');
const { Options, ServiceBuilder } = require('selenium-webdriver/chrome');
const axios = require('axios');
const fs = require('fs');
const { serialize } = require('cookie');

//*[@id="app"]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video
///html/body/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/video

let options = new Options();
// options.addArguments('--headless=new');
options.setChromeBinaryPath(process.env.CHROME_BINARY_PATH)
options.addArguments('--disable-3d-apis');
// options.addArguments('--disable-dev-shm-usage'); //This will force Chrome to use the /tmp directory instead. Fixing issue with tab crashing due to Heroku attempting to always use /dev/shm for non-executable memory.
options.addArguments('--disable-gpu'); //Disables GPU hardware acceleration. If software renderer is not in place, then the GPU process won't launch.
options.addArguments('--no-sandbox'); //Disables the sandbox. The Google sandbox is a development and test environment for developers working on Google Chrome browser-based applications. Disabling this to run on heroku

client.login(process.env.TOKEN);

client.once('ready', () => {
    console.log('Ready to go!');
})

client.on('message', async message =>{
    client.user.setActivity('tiktoks', {type:'WATCHING'})

    if(!message.content.includes(".tiktok.com/") || message.author.bot) return;

    // message.lineReply("Message Read");D

    let serviceBuilder = new ServiceBuilder('./lib/chromedriver.exe')
    // let serviceBuilder = new ServiceBuilder('./lib/chrome.exe')
    let driver = new webdriver.Builder().setChromeOptions(options).withCapabilities(webdriver.Capabilities.chrome()).setChromeService(serviceBuilder).build();

    try {
        await driver.get(message.content);
        await driver.wait(webdriver.until.elementLocated(webdriver.By.css('video')), 20000);
        let element = await driver.findElement(webdriver.By.css('video'));
        
        const url = await element.getAttribute('src')
        await driver.navigate().to(url);

        if (fs.existsSync('output.mp4')) {  //temp file for video output
            fs.unlinkSync('output.mp4');
        }
        const output = await fs.createWriteStream('output.mp4');

        await driver.get(url)

        const cookies = await driver.manage().getCookies()

        const cookieString = cookies.map(cookie => {
            return serialize(cookie.name, cookie.value, cookie);
            }).join('; ');

        const res = await axios.get(url, {
                            // withCredentials: true,
                            responseType: 'stream', 
                            headers: {
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", 
                                "Accept-Encoding": "gzip, deflate, br", 
                                "Accept-Language": "en-US,en;q=0.9", 
                                "Cookie":cookieString,
                                "Host":"v16-webapp-prime.us.tiktok.com",
                                "Referer":"https://www.tiktok.com/",
                                "Sec-Ch-Ua": "\"Google Chrome\";v=\"113\", \"Chromium\";v=\"113\", \"Not-A.Brand\";v=\"24\"", 
                                "Sec-Ch-Ua-Mobile": "?0", 
                                "Sec-Ch-Ua-Platform": "\"Windows\"", 
                                "Sec-Fetch-Dest": "document", 
                                "Sec-Fetch-Mode": "navigate", 
                                "Sec-Fetch-Site": "cross-site", 
                                "Sec-Fetch-User": "?1", 
                                "Upgrade-Insecure-Requests": "1", 
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36", 
                                "X-Amzn-Trace-Id": "Root=1-645b4577-403eadd84e8f060c7760e4ef"
                                }
                        });

        const stream = await res.data;

        await stream.on('data', (chunk) => {     // chunk is an ArrayBuffer
            output.write(new Buffer.from(chunk));
        });
        await stream.on('end', () => {
            output.end();
            const attachment = new MessageAttachment('\output.mp4');
            message.lineReply("", attachment)
                .catch((error)=>{
                    console.log('Caught: ', error.name, error.message)
                    message.lineReply("Sorry. File is larger than Discord's 8MB Limitation.")
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
            console.log('Caught: ', error.name, error)
            message.lineReply(error.toString());
          }
    } finally {
        // await driver.quit();
    }
}    
);
