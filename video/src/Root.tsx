import React from "react";
import { Composition } from "remotion";
import { Lovelight, TOTAL_FRAMES } from "./Video";

export const RemotionRoot: React.FC = () => (
  <Composition id="Lovelight" component={Lovelight} durationInFrames={TOTAL_FRAMES} fps={30} width={1920} height={1080} />
);
