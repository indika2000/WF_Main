import React, { useEffect, useMemo } from "react";
import { View, StyleSheet } from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
  withDelay,
  Easing,
  interpolate,
} from "react-native-reanimated";

export type ShimmerRarity = "common" | "uncommon" | "rare" | "epic" | "legendary";

interface CardShimmerProps {
  rarity: ShimmerRarity;
  width: number;
  height: number;
}

interface RarityConfig {
  // Light sweep
  sweepColor: string;
  sweepWidth: number;
  sweepSpeed: number;
  // Floating light motes
  moteCount: number;
  moteColors: string[];
  moteMinSize: number;
  moteMaxSize: number;
  // Edge highlight
  edgeColor: string;
  edgeOpacity: number;
}

const CONFIGS: Record<ShimmerRarity, RarityConfig> = {
  common: {
    sweepColor: "transparent",
    sweepWidth: 0,
    sweepSpeed: 0,
    moteCount: 0,
    moteColors: [],
    moteMinSize: 0,
    moteMaxSize: 0,
    edgeColor: "transparent",
    edgeOpacity: 0,
  },
  uncommon: {
    sweepColor: "rgba(255,255,255,0.07)",
    sweepWidth: 120,
    sweepSpeed: 3000,
    moteCount: 5,
    moteColors: ["rgba(255,255,255,0.4)", "rgba(200,220,255,0.3)"],
    moteMinSize: 1.5,
    moteMaxSize: 3,
    edgeColor: "rgba(192,192,192,0.15)",
    edgeOpacity: 0.15,
  },
  rare: {
    sweepColor: "rgba(255,225,100,0.09)",
    sweepWidth: 140,
    sweepSpeed: 2600,
    moteCount: 10,
    moteColors: [
      "rgba(255,235,59,0.5)",
      "rgba(255,215,0,0.4)",
      "rgba(255,255,200,0.5)",
    ],
    moteMinSize: 1.5,
    moteMaxSize: 4,
    edgeColor: "rgba(255,215,0,0.12)",
    edgeOpacity: 0.2,
  },
  epic: {
    sweepColor: "rgba(255,255,255,0.1)",
    sweepWidth: 160,
    sweepSpeed: 2200,
    moteCount: 16,
    moteColors: [
      "rgba(255,120,120,0.45)",
      "rgba(255,200,80,0.45)",
      "rgba(120,255,150,0.45)",
      "rgba(120,180,255,0.45)",
      "rgba(200,120,255,0.45)",
    ],
    moteMinSize: 1.5,
    moteMaxSize: 4.5,
    edgeColor: "rgba(180,100,255,0.12)",
    edgeOpacity: 0.25,
  },
  legendary: {
    sweepColor: "rgba(255,240,180,0.12)",
    sweepWidth: 180,
    sweepSpeed: 1800,
    moteCount: 24,
    moteColors: [
      "rgba(255,100,100,0.55)",
      "rgba(255,200,50,0.55)",
      "rgba(255,255,100,0.55)",
      "rgba(100,255,150,0.55)",
      "rgba(100,200,255,0.55)",
      "rgba(220,100,255,0.55)",
      "rgba(255,100,220,0.55)",
      "rgba(255,255,255,0.6)",
    ],
    moteMinSize: 2,
    moteMaxSize: 5,
    edgeColor: "rgba(255,200,50,0.15)",
    edgeOpacity: 0.3,
  },
};

function seededRandom(seed: number) {
  const x = Math.sin(seed * 9301 + 49297) * 49297;
  return x - Math.floor(x);
}

// A soft light sweep that glides diagonally across the card
function LightSweep({
  color,
  sweepWidth,
  speed,
  cardWidth,
  cardHeight,
}: {
  color: string;
  sweepWidth: number;
  speed: number;
  cardWidth: number;
  cardHeight: number;
}) {
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withRepeat(
      withSequence(
        withTiming(1, { duration: speed, easing: Easing.inOut(Easing.ease) }),
        withDelay(800, withTiming(0, { duration: 0 })),
      ),
      -1,
      false
    );
  }, []);

  const style = useAnimatedStyle(() => {
    const translateX = interpolate(
      progress.value,
      [0, 1],
      [-sweepWidth * 1.5, cardWidth + sweepWidth]
    );
    const opacity = interpolate(
      progress.value,
      [0, 0.2, 0.5, 0.8, 1],
      [0, 0.6, 1, 0.6, 0]
    );
    return {
      transform: [{ translateX }, { rotate: "15deg" }],
      opacity,
    };
  });

  return (
    <Animated.View
      style={[
        {
          position: "absolute",
          top: -cardHeight * 0.15,
          width: sweepWidth,
          height: cardHeight * 1.4,
          backgroundColor: color,
        },
        style,
      ]}
      pointerEvents="none"
    />
  );
}

// Tiny floating light mote - like dust catching light
function LightMote({
  x,
  y,
  size,
  color,
  delay,
  floatDuration,
  cardHeight,
}: {
  x: number;
  y: number;
  size: number;
  color: string;
  delay: number;
  floatDuration: number;
  cardHeight: number;
}) {
  const life = useSharedValue(0);
  const drift = useSharedValue(0);

  useEffect(() => {
    life.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(1, {
            duration: floatDuration * 0.35,
            easing: Easing.out(Easing.quad),
          }),
          withTiming(0.6, {
            duration: floatDuration * 0.3,
            easing: Easing.inOut(Easing.ease),
          }),
          withTiming(0, {
            duration: floatDuration * 0.35,
            easing: Easing.in(Easing.quad),
          }),
        ),
        -1,
        false
      )
    );

    drift.value = withDelay(
      delay,
      withRepeat(
        withTiming(-15, {
          duration: floatDuration,
          easing: Easing.inOut(Easing.ease),
        }),
        -1,
        true
      )
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    opacity: life.value * life.value, // ease-in curve for softer appearance
    transform: [
      { translateY: drift.value },
      { scale: interpolate(life.value, [0, 0.5, 1], [0.3, 1, 0.8]) },
    ],
  }));

  return (
    <Animated.View
      style={[
        {
          position: "absolute",
          left: x - size,
          top: y - size,
          width: size * 2,
          height: size * 2,
        },
        style,
      ]}
      pointerEvents="none"
    >
      {/* Soft glow */}
      <View
        style={{
          width: size * 2,
          height: size * 2,
          borderRadius: size,
          backgroundColor: color,
        }}
      />
      {/* Bright center pinpoint */}
      <View
        style={{
          position: "absolute",
          left: size - size * 0.3,
          top: size - size * 0.3,
          width: size * 0.6,
          height: size * 0.6,
          borderRadius: size * 0.3,
          backgroundColor: "rgba(255,255,255,0.8)",
        }}
      />
    </Animated.View>
  );
}

// Pulsing edge highlight border
function EdgeGlow({
  color,
  maxOpacity,
  speed,
}: {
  color: string;
  maxOpacity: number;
  speed: number;
}) {
  const pulse = useSharedValue(0);

  useEffect(() => {
    pulse.value = withRepeat(
      withSequence(
        withTiming(1, {
          duration: speed * 0.6,
          easing: Easing.inOut(Easing.ease),
        }),
        withTiming(0.2, {
          duration: speed * 0.4,
          easing: Easing.inOut(Easing.ease),
        }),
      ),
      -1,
      true
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    opacity: interpolate(pulse.value, [0, 1], [maxOpacity * 0.2, maxOpacity]),
  }));

  return (
    <Animated.View
      style={[
        StyleSheet.absoluteFill,
        {
          borderRadius: 16,
          borderWidth: 1.5,
          borderColor: color,
        },
        style,
      ]}
      pointerEvents="none"
    />
  );
}

export default function CardShimmer({ rarity, width, height }: CardShimmerProps) {
  const config = CONFIGS[rarity];

  const motes = useMemo(() => {
    if (rarity === "common") return [];
    return Array.from({ length: config.moteCount }, (_, i) => {
      const seed = i + 1;
      return {
        id: i,
        x: seededRandom(seed) * width * 0.85 + width * 0.075,
        y: seededRandom(seed + 100) * height * 0.85 + height * 0.075,
        size:
          config.moteMinSize +
          seededRandom(seed + 200) * (config.moteMaxSize - config.moteMinSize),
        color: config.moteColors[Math.floor(seededRandom(seed + 300) * config.moteColors.length)],
        delay: seededRandom(seed + 400) * 4000,
        floatDuration: 2000 + seededRandom(seed + 500) * 2500,
      };
    });
  }, [rarity, width, height]);

  if (rarity === "common") return null;

  return (
    <View style={[StyleSheet.absoluteFill, { overflow: "hidden", borderRadius: 16 }]} pointerEvents="none">
      {/* Light sweep */}
      <LightSweep
        color={config.sweepColor}
        sweepWidth={config.sweepWidth}
        speed={config.sweepSpeed}
        cardWidth={width}
        cardHeight={height}
      />

      {/* Floating light motes */}
      {motes.map((m) => (
        <LightMote
          key={m.id}
          x={m.x}
          y={m.y}
          size={m.size}
          color={m.color}
          delay={m.delay}
          floatDuration={m.floatDuration}
          cardHeight={height}
        />
      ))}

      {/* Edge glow */}
      <EdgeGlow
        color={config.edgeColor}
        maxOpacity={config.edgeOpacity}
        speed={config.sweepSpeed}
      />
    </View>
  );
}
