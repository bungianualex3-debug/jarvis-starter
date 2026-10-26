// Check stills with one bundle: node src/stills.mjs <frame> <frame> ...  -> out/check/f<frame>.jpeg
// Look at these before every full render: a full render costs minutes, a still costs seconds.
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';

const frames = process.argv.slice(2).map(Number);
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const composition = await selectComposition({serveUrl, id: 'Launch'});
fs.mkdirSync('out/check', {recursive: true});
for (const frame of frames) {
  await renderStill({
    serveUrl,
    composition,
    frame,
    output: `out/check/f${String(frame).padStart(4, '0')}.jpeg`,
    imageFormat: 'jpeg',
    scale: 0.3,
    timeoutInMilliseconds: 240000,
  });
  process.stdout.write(frame + ' ');
}
console.log('done');
