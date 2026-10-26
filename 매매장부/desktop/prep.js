// 장부 파일(../주식매매장부.html)을 앱 폴더(web/)로 복사한다. 빌드·실행 전에 자동으로 호출된다.
const fs = require('fs');
const path = require('path');
const src = path.join(__dirname, '..', '주식매매장부.html');
const web = path.join(__dirname, 'web');
fs.mkdirSync(web, { recursive: true });
fs.copyFileSync(src, path.join(web, 'index.html'));
console.log('web/index.html <-', src);
