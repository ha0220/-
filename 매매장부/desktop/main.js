'use strict';
const { app, BrowserWindow, Menu, protocol, net, shell, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { pathToFileURL } = require('url');

const SELFTEST = process.argv.includes('--selftest');
const OUT_ARG = process.argv.find(a => a.startsWith('--selftest-out='));
const SELFTEST_OUT = OUT_ARG ? OUT_ARG.slice('--selftest-out='.length) : null;
const WEB_ROOT = path.join(__dirname, 'web');
const BACKUP_RE = /^매매장부_백업_\d{4}-\d{2}-\d{2}\.json$/;
const ORIGIN = 'app://ledger/';

// 자체 점검은 실제 장부 데이터와 섞이지 않도록 임시 폴더를 쓴다
if (SELFTEST) app.setPath('userData', fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-selftest-')));

// 경로와 상관없이 항상 같은 주소(app://ledger)로 열어 브라우저 저장공간(장부 데이터)이 유지되게 한다
protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } }
]);

const configPath = () => path.join(app.getPath('userData'), 'config.json');
function readConfig() { try { return JSON.parse(fs.readFileSync(configPath(), 'utf8')); } catch (e) { return {}; } }
function writeConfig(c) {
  fs.mkdirSync(path.dirname(configPath()), { recursive: true });
  fs.writeFileSync(configPath(), JSON.stringify(c, null, 2));
}
function backupDir() {
  const d = readConfig().backupDir || '';
  try { return d && fs.statSync(d).isDirectory() ? d : ''; } catch (e) { return ''; }
}
function writeBackup(name, text) {
  if (typeof name !== 'string' || !BACKUP_RE.test(name)) throw new Error('잘못된 백업 파일 이름');
  if (typeof text !== 'string' || text.length > 200 * 1024 * 1024) throw new Error('잘못된 백업 내용');
  const dir = backupDir();
  if (!dir) throw new Error('백업 폴더가 없습니다');
  const target = path.join(dir, name), tmp = target + '.tmp';
  fs.writeFileSync(tmp, text, 'utf8');
  fs.renameSync(tmp, target);
  return true;
}
function latestBackup() {
  const dir = backupDir();
  if (!dir) return null;
  const names = fs.readdirSync(dir).filter(n => BACKUP_RE.test(n)).sort();
  if (!names.length) return null;
  const name = names[names.length - 1];
  return { name, text: fs.readFileSync(path.join(dir, name), 'utf8') };
}

ipcMain.handle('ledger:get-dir', () => backupDir());
ipcMain.handle('ledger:pick-dir', async e => {
  const win = BrowserWindow.fromWebContents(e.sender);
  const r = await dialog.showOpenDialog(win, { title: '백업 폴더 선택 (예: 구글 드라이브의 주식매매 폴더)', properties: ['openDirectory', 'createDirectory'] });
  if (r.canceled || !r.filePaths.length) return '';
  writeConfig({ ...readConfig(), backupDir: r.filePaths[0] });
  return r.filePaths[0];
});
ipcMain.handle('ledger:clear-dir', () => { const c = readConfig(); delete c.backupDir; writeConfig(c); return true; });
ipcMain.handle('ledger:write', (e, name, text) => writeBackup(name, text));
ipcMain.handle('ledger:latest', () => latestBackup());

function createWindow() {
  const win = new BrowserWindow({
    width: 1280, height: 880, minWidth: 360, minHeight: 480,
    show: !SELFTEST, title: '주식 매매 관리 장부', autoHideMenuBar: true,
    icon: path.join(__dirname, 'build', 'icon.png'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true }
  });
  const external = url => { if (/^https?:\/\//.test(url)) shell.openExternal(url); };
  win.webContents.setWindowOpenHandler(({ url }) => { external(url); return { action: 'deny' }; });
  win.webContents.on('will-navigate', (e, url) => { if (!url.startsWith(ORIGIN)) { e.preventDefault(); external(url); } });
  win.loadURL(ORIGIN + 'index.html');
  return win;
}

async function selftest(win) {
  const res = { ok: false, steps: {} };
  const out = o => { if (SELFTEST_OUT) fs.writeFileSync(SELFTEST_OUT, JSON.stringify(o, null, 2)); console.log('SELFTEST ' + JSON.stringify(o)); };
  try {
    await new Promise((ok, no) => { win.webContents.once('did-finish-load', ok); win.webContents.once('did-fail-load', (e, c, d) => no(new Error(d))); });
    const page = await win.webContents.executeJavaScript(`(async()=>{
      await new Promise(r=>setTimeout(r,300));
      localStorage.setItem('__t','1');const ls=localStorage.getItem('__t')==='1';localStorage.removeItem('__t');
      return {ledger:typeof window.__ledger==='object',tabs:document.querySelectorAll('#tabs button').length,
        native:typeof window.ledgerNative==='object',ls,protocol:location.protocol,secure:window.isSecureContext,
        dirNote:document.getElementById('dirNote').textContent.slice(0,40)};
    })()`);
    res.steps.page = page;
    // 폴더 연결 → 화면의 백업 버튼 → 파일 생성
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-bk-'));
    writeConfig({ backupDir: tmp });
    const conn = await win.webContents.executeJavaScript(`(async()=>{
      const d=await window.ledgerNative.getDir();
      const a=await window.ledgerNative.writeBackup('매매장부_백업_2026-01-02.json','{"a":1}');
      const b=await window.ledgerNative.writeBackup('매매장부_백업_2026-03-04.json','{"b":2}');
      const l=await window.ledgerNative.latestBackup();
      let bad='no-error';try{await window.ledgerNative.writeBackup('../evil.json','x')}catch(e){bad='rejected'}
      return {d,a,b,latest:l&&l.name,text:l&&l.text,bad};
    })()`);
    res.steps.ipc = conn;
    // 앱이 연결된 폴더를 인식하고 백업 버튼으로 파일을 만드는지(앱을 다시 불러와 폴더 연결 상태에서 시작)
    win.loadURL(ORIGIN + 'index.html');
    await new Promise(ok => win.webContents.once('did-finish-load', ok));
    await win.webContents.executeJavaScript(`new Promise(r=>setTimeout(r,500))`);
    const note = await win.webContents.executeJavaScript(`document.getElementById('dirNote').textContent`);
    await win.webContents.executeJavaScript(`document.getElementById('btnBackup').click()`);
    let file = null;
    for (let i = 0; i < 50 && !file; i++) {
      await new Promise(r => setTimeout(r, 100));
      file = fs.readdirSync(tmp).find(n => BACKUP_RE.test(n) && !n.includes('2026-01-02') && !n.includes('2026-03-04'));
    }
    let parsed = null;
    if (file) { try { parsed = JSON.parse(fs.readFileSync(path.join(tmp, file), 'utf8')); } catch (e) {} }
    res.steps.backup = { note: note.slice(0, 40), file, hasTrades: !!(parsed && Array.isArray(parsed.trades)), hasLastBackup: !!(parsed && parsed.lastBackup) };
    const p = res.steps.page, i = res.steps.ipc, b = res.steps.backup;
    res.ok = p.ledger && p.tabs >= 8 && p.native && p.ls && p.protocol === 'app:' && p.secure &&
      i.d === tmp && i.a === true && i.b === true && i.latest === '매매장부_백업_2026-03-04.json' && i.text === '{"b":2}' && i.bad === 'rejected' &&
      b.note.includes('연결됨') && !!b.file && b.hasTrades && b.hasLastBackup;
  } catch (e) { res.error = String(e && e.stack || e); }
  out(res);
  app.exit(res.ok ? 0 : 1);
}

if (!app.requestSingleInstanceLock() && !SELFTEST) app.quit();
else {
  app.whenReady().then(() => {
    protocol.handle('app', req => {
      const u = new URL(req.url);
      let p = decodeURIComponent(u.pathname);
      if (p === '/' || p === '') p = '/index.html';
      const file = path.normalize(path.join(WEB_ROOT, p));
      if (!file.startsWith(WEB_ROOT)) return new Response('forbidden', { status: 403 });
      return net.fetch(pathToFileURL(file).toString());
    });
    Menu.setApplicationMenu(Menu.buildFromTemplate([{ role: 'editMenu' }, { role: 'viewMenu' }]));
    const win = createWindow();
    if (SELFTEST) selftest(win);
  });
  app.on('second-instance', () => { const w = BrowserWindow.getAllWindows()[0]; if (w) { if (w.isMinimized()) w.restore(); w.focus(); } });
  app.on('window-all-closed', () => app.quit());
}
