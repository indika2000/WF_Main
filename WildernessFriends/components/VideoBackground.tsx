import React, { useRef, useState } from "react";
import { StyleSheet, View } from "react-native";
import { Video, ResizeMode, AVPlaybackSource } from "expo-av";

interface VideoBackgroundProps {
  source: AVPlaybackSource;
  backgroundColor?: string;
}

export default function VideoBackground({
  source,
  backgroundColor = "#ffffff",
}: VideoBackgroundProps) {
  const videoRef = useRef(null);
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <View
        style={[StyleSheet.absoluteFill, { backgroundColor }]}
      />
    );
  }

  return (
    <View style={[StyleSheet.absoluteFill, { backgroundColor }]}>
      <Video
        ref={videoRef}
        source={source}
        style={{
          position: "absolute",
          top: "-12%",
          left: "-5%",
          width: "110%",
          height: "110%",
        }}
        resizeMode={ResizeMode.CONTAIN}
        shouldPlay
        isLooping
        isMuted
        onError={() => setHasError(true)}
      />
    </View>
  );
}
