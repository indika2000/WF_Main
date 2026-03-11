import React, { useRef } from "react";
import { View, StyleSheet, ActivityIndicator, Text, Dimensions } from "react-native";
import { Video, ResizeMode, AVPlaybackStatus } from "expo-av";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");
const VIDEO_WIDTH = SCREEN_WIDTH * 0.8;
const VIDEO_HEIGHT = SCREEN_HEIGHT * 0.65;

interface PackOpeningVideoProps {
  visible: boolean;
  onVideoEnd: () => void;
  showLoadingIndicator?: boolean;
}

export default function PackOpeningVideo({
  visible,
  onVideoEnd,
  showLoadingIndicator = false,
}: PackOpeningVideoProps) {
  const videoRef = useRef<Video>(null);

  if (!visible) return null;

  const handlePlaybackStatusUpdate = (status: AVPlaybackStatus) => {
    if (status.isLoaded && status.didJustFinish) {
      onVideoEnd();
    }
  };

  return (
    <View style={styles.overlay}>
      {/* Dark transparent backdrop */}
      <View style={styles.backdrop} />

      {/* Centered video modal */}
      <View style={styles.videoContainer}>
        <Video
          ref={videoRef}
          source={require("../assets/images/character_creator/pack-opening.mp4")}
          style={styles.video}
          resizeMode={ResizeMode.CONTAIN}
          shouldPlay
          isLooping={false}
          isMuted={false}
          onPlaybackStatusUpdate={handlePlaybackStatusUpdate}
        />
        {showLoadingIndicator && (
          <View style={styles.loadingOverlay}>
            <ActivityIndicator size="large" color="#7B8F6B" />
            <Text style={styles.loadingText}>Summoning creature...</Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
    zIndex: 100,
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0, 0, 0, 0.7)",
  },
  videoContainer: {
    width: VIDEO_WIDTH,
    height: VIDEO_HEIGHT,
    borderRadius: 16,
    overflow: "hidden",
    backgroundColor: "#000",
    elevation: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.5,
    shadowRadius: 12,
  },
  video: {
    width: "100%",
    height: "100%",
  },
  loadingOverlay: {
    position: "absolute",
    bottom: 30,
    left: 0,
    right: 0,
    alignItems: "center",
  },
  loadingText: {
    color: "#E8E0D4",
    fontSize: 14,
    fontWeight: "600",
    marginTop: 8,
    textShadowColor: "rgba(0,0,0,0.8)",
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
});
