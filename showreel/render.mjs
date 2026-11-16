// Render showreel.html frame-by-frame and pipe to ffmpeg.
// Usage:
//   node render.mjs                      -> full video (showreel.mp4)
//   node render.mjs --stills 0.5,3,8     -> PNG stills into ./stills
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const dir = path.dirname(fileURLToPath(import.meta.url));
const FPS = 60;
const args = process.argv.slice(2);
const stillsArg = args.includes('--stills') ? args[args.indexOf('--stills') + 1] : null;
const out = args.includes('--out') ? args[args.indexOf('--out') + 1] : path.join(dir, 'showreel.mp4');

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto('file://' + path.join(dir, 'showreel.html') + '?render');
await page.evaluate(() => window.ready);

const grab = async t => {
  const b64 = await page.evaluate(t => {
    window.render(t);
    return document.getElementById('c').toDataURL('image/png').split(',')[1];
  }, t);
  return Buffer.from(b64, 'base64');
};

if (stillsArg) {
  mkdirSync(path.join(dir, 'stills'), { recursive: true });
  for (const s of stillsArg.split(',').map(Number)) {
    writeFileSync(path.join(dir, 'stills', `t${s.toFixed(2)}.png`), await grab(s));
  }
} else {
  const dur = await page.evaluate(() => window.DURATION);
  const audio = path.join(dir, 'audio.wav');
  const ff = spawn('ffmpeg', [
    '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    ...(existsSync(audio) ? ['-i', audio, '-c:a', 'aac', '-b:a', '256k', '-shortest'] : []),
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p',
    '-profile:v', 'high', '-movflags', '+faststart', out,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  const N = Math.round(dur * FPS);
  for (let i = 0; i < N; i++) {
    const buf = await grab(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 60 === 0) process.stderr.write(`frame ${i}/${N}\n`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
}
await browser.close();
