const request = require('request');
// const test = new Request('https://www.tiktok.com/@_mrforgetable/video/7063596664170335534?_t=8PqbYUHBm62&_r=1')

request('https://vm.tiktok.com/TTPdBk4Nyj/', function(error, response, html){
    console.error('error:', error);
    console.log('statusCode: ', response && response.statusCode);
    console.log('html: ', html);
});