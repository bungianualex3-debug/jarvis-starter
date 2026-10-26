import React from 'react';
import {Composition} from 'remotion';
import {Launch, TOTAL} from './Launch';

// Render: npx remotion render src/index.ts Launch out/video.mp4 --concurrency=3 --timeout=300000
export const EditorRoot: React.FC = () => (
  <Composition id="Launch" component={Launch} durationInFrames={TOTAL} fps={30} width={1080} height={1920} />
);
