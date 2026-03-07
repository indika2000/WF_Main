import React, { useEffect } from "react";
import { View, Text, StyleSheet, ImageSourcePropType, Image } from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  interpolate,
  Easing,
} from "react-native-reanimated";

interface LayeredFlipCardProps {
  isFlipped: boolean;
  baseImage: ImageSourcePropType;
  characterImage: ImageSourcePropType;
  borderImage: ImageSourcePropType;
  backImage: ImageSourcePropType;
  lightText?: boolean;
  width?: number;
  height?: number;
  duration?: number;
}

export default function LayeredFlipCard({
  isFlipped,
  baseImage,
  characterImage,
  borderImage,
  backImage,
  lightText = false,
  width = 260,
  height = 380,
  duration = 800,
}: LayeredFlipCardProps) {
  // Character layer scaled down and centered (adjust 0.85 to taste)
  const charScale = 0.98;
  const charW = width * charScale;
  const charH = height * charScale;
  const charLeft = (width - charW) / 2;
  const charTop = (height - charH) / 2;
  const rotation = useSharedValue(0);

  useEffect(() => {
    rotation.value = withTiming(isFlipped ? 180 : 0, {
      duration,
      easing: Easing.inOut(Easing.ease),
    });
  }, [isFlipped]);

  const frontAnimatedStyle = useAnimatedStyle(() => {
    const rotateY = interpolate(rotation.value, [0, 180], [180, 360]);
    return {
      transform: [
        { perspective: 1200 },
        { rotateY: `${rotateY}deg` },
      ],
      backfaceVisibility: "hidden" as const,
    };
  });

  const backAnimatedStyle = useAnimatedStyle(() => {
    const rotateY = interpolate(rotation.value, [0, 180], [0, 180]);
    return {
      transform: [
        { perspective: 1200 },
        { rotateY: `${rotateY}deg` },
      ],
      backfaceVisibility: "hidden" as const,
    };
  });

  return (
    <View style={[styles.container, { width, height }]}>
      {/* Back of card (visible initially) */}
      <Animated.View style={[styles.card, { width, height }, backAnimatedStyle]}>
        <Image
          source={backImage}
          style={styles.cardImage}
          resizeMode="cover"
        />
      </Animated.View>

      {/* Front of card (visible after flip) — 3 stacked layers */}
      <Animated.View style={[styles.card, { width, height }, frontAnimatedStyle]}>
        <Image
          source={baseImage}
          style={{ position: "absolute", top: 0, left: 0, width, height }}
          resizeMode="cover"
        />
        <Image
          source={characterImage}
          style={{ position: "absolute", top: charTop, left: charLeft, width: charW, height: charH }}
          resizeMode="contain"
        />
        <Image
          source={borderImage}
          style={{ position: "absolute", top: 0, left: 0, width, height }}
          resizeMode="cover"
        />
        <Text
          style={{
            position: "absolute",
            bottom: 6,
            right: 8,
            fontFamily: "serif",
            fontSize: width * 0.035,
            color: lightText ? "#ffffff" : "#000000",
          }}
        >
          {"\u2122"} 2026 Caps and Capes
        </Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
  },
  card: {
    position: "absolute",
    borderRadius: 16,
    overflow: "hidden",
    elevation: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  cardImage: {
    width: "100%",
    height: "100%",
  },
});
