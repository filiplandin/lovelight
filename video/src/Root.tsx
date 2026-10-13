import React from "react";
import { Composition } from "remotion";
import { LI_TOTAL, LovelightLinkedIn } from "./linkedin/LinkedIn";
import { Lovelight, TOTAL_FRAMES } from "./Video";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Lovelight" component={Lovelight} durationInFrames={TOTAL_FRAMES} fps={30} width={1920} height={1080} />
    <Composition id="LovelightLinkedIn" component={LovelightLinkedIn} durationInFrames={LI_TOTAL} fps={30} width={1080} height={1350} />
  </>
);
