import React, { useEffect } from "react";
import { View, Text, StyleSheet, ImageSourcePropType, Image } from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  interpolate,
  Easing,
} from "react-native-reanimated";
import CardShimmer, { ShimmerRarity } from "./CardShimmer";

interface FlipCardProps {
  isFlipped: boolean;
  frontImage: ImageSourcePropType;
  backImage: ImageSourcePropType;
  scannedText?: string;
  rarity?: ShimmerRarity;
  width?: number;
  height?: number;
  duration?: number;
}

export default function FlipCard({
  isFlipped,
  frontImage,
  backImage,
  scannedText,
  rarity = "rare",
  width = 260,
  height = 380,
  duration = 800,
}: FlipCardProps) {
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

      {/* Front of card (visible after flip) */}
      <Animated.View style={[styles.card, styles.cardFront, { width, height }, frontAnimatedStyle]}>
        <Image
          source={frontImage}
          style={styles.cardImage}
          resizeMode="cover"
        />
        {/* Shimmer overlay */}
        <CardShimmer rarity={rarity} width={width} height={height} />
        {scannedText && (
          <View style={styles.textOverlay}>
            <View style={styles.textBox}>
              <Text style={styles.scannedLabel}>SCANNED</Text>
              <Text style={styles.scannedText} selectable>
                {scannedText}
              </Text>
            </View>
          </View>
        )}
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
  cardFront: {
    // Stacked on top of back
  },
  cardImage: {
    width: "100%",
    height: "100%",
  },
  textOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 20,
  },
  textBox: {
    backgroundColor: "rgba(15, 26, 20, 0.85)",
    borderRadius: 12,
    paddingVertical: 16,
    paddingHorizontal: 20,
    alignItems: "center",
    maxWidth: "90%",
    borderWidth: 1,
    borderColor: "rgba(139, 177, 116, 0.4)",
  },
  scannedLabel: {
    color: "#8BB174",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 2,
    marginBottom: 6,
  },
  scannedText: {
    color: "#ffffff",
    fontSize: 14,
    fontWeight: "500",
    textAlign: "center",
    lineHeight: 20,
  },
});
