import React, { useEffect } from "react";
import { View, Text, StyleSheet, Dimensions } from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  withDelay,
  withSequence,
  Easing,
  interpolate,
} from "react-native-reanimated";

const { width: W, height: H } = Dimensions.get("window");

interface Props {
  visible: boolean;
}

// Expanding sonar ring — each ring pulses outward from centre and fades
function SonarRing({
  delay,
  maxRadius,
  color,
}: {
  delay: number;
  maxRadius: number;
  color: string;
}) {
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withDelay(
      delay,
      withRepeat(
        withTiming(1, { duration: 2400, easing: Easing.out(Easing.cubic) }),
        -1,
        false
      )
    );
  }, []);

  const style = useAnimatedStyle(() => {
    const r = interpolate(progress.value, [0, 1], [20, maxRadius]);
    return {
      width: r * 2,
      height: r * 2,
      borderRadius: r,
      left: W / 2 - r,
      top: H / 2 - r,
      opacity: interpolate(progress.value, [0, 0.3, 1], [0, 0.6, 0]),
      borderColor: color,
    };
  });

  return (
    <Animated.View
      style={[styles.sonarRing, style]}
      pointerEvents="none"
    />
  );
}

// Pulsing amber orb at centre
function AmberOrb() {
  const scale = useSharedValue(1);

  useEffect(() => {
    scale.value = withRepeat(
      withSequence(
        withTiming(1.2, { duration: 900, easing: Easing.inOut(Easing.ease) }),
        withTiming(0.88, { duration: 800, easing: Easing.inOut(Easing.ease) }),
      ),
      -1,
      true
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const ORB = 46;

  return (
    <Animated.View
      style={[
        {
          position: "absolute",
          width: ORB,
          height: ORB,
          borderRadius: ORB / 2,
          left: W / 2 - ORB / 2,
          top: H / 2 - ORB / 2,
          backgroundColor: "rgba(251,191,36,0.18)",
          borderWidth: 1.5,
          borderColor: "rgba(251,191,36,0.65)",
        },
        style,
      ]}
      pointerEvents="none"
    >
      <View
        style={{
          position: "absolute",
          width: 16,
          height: 16,
          borderRadius: 8,
          left: 15,
          top: 15,
          backgroundColor: "rgba(255,235,160,0.85)",
        }}
      />
    </Animated.View>
  );
}

// Drifting mist strip
function MistStrip({
  y,
  delay,
  width,
}: {
  y: number;
  delay: number;
  width: number;
}) {
  const opacity = useSharedValue(0);
  const translateX = useSharedValue(-width * 0.3);

  useEffect(() => {
    opacity.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(0.22, { duration: 1800, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.08, { duration: 1800, easing: Easing.inOut(Easing.ease) }),
        ),
        -1,
        true
      )
    );
    translateX.value = withDelay(
      delay,
      withRepeat(
        withTiming(width * 0.15, { duration: 6000, easing: Easing.inOut(Easing.ease) }),
        -1,
        true
      )
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [{ translateX: translateX.value }],
  }));

  return (
    <Animated.View
      style={[
        {
          position: "absolute",
          left: 0,
          top: y,
          width,
          height: 28,
          backgroundColor: "rgba(45,90,69,0.4)",
          borderRadius: 14,
        },
        style,
      ]}
      pointerEvents="none"
    />
  );
}

// Text with animated ellipsis
function WaitingText() {
  const opacity = useSharedValue(1);

  useEffect(() => {
    opacity.value = withRepeat(
      withSequence(
        withTiming(0.55, { duration: 1100, easing: Easing.inOut(Easing.ease) }),
        withTiming(1, { duration: 1100, easing: Easing.inOut(Easing.ease) }),
      ),
      -1,
      false
    );
  }, []);

  const style = useAnimatedStyle(() => ({ opacity: opacity.value }));

  return (
    <View style={styles.textBlock}>
      <Animated.Text style={[styles.titleText, style]}>
        Almost found your creature...
      </Animated.Text>
      <Text style={styles.subtitleText}>Your creature is awakening</Text>
      <SpinnerDots />
    </View>
  );
}

function SpinnerDots() {
  return (
    <View style={styles.dotsRow}>
      {[0, 300, 600, 900].map((delay, i) => (
        <PulsingDot key={i} delay={delay} />
      ))}
    </View>
  );
}

function PulsingDot({ delay }: { delay: number }) {
  const scale = useSharedValue(0.4);

  useEffect(() => {
    scale.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(1, { duration: 400, easing: Easing.out(Easing.quad) }),
          withTiming(0.4, { duration: 400, easing: Easing.in(Easing.quad) }),
          withTiming(0.4, { duration: 400 }),
        ),
        -1,
        false
      )
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: interpolate(scale.value, [0.4, 1], [0.3, 1]),
  }));

  return (
    <Animated.View style={[styles.dot, style]} />
  );
}

export default function CreatureAlmostFoundAnimation({ visible }: Props) {
  if (!visible) return null;

  const mistStrips = [
    { y: H * 0.72, delay: 0, width: W * 0.7 },
    { y: H * 0.77, delay: 800, width: W * 0.55 },
    { y: H * 0.82, delay: 400, width: W * 0.85 },
    { y: H * 0.87, delay: 1200, width: W * 0.5 },
  ];

  return (
    <View style={styles.container} pointerEvents="none">
      {/* Sonar rings — 4 with staggered delays */}
      <SonarRing delay={0} maxRadius={160} color="rgba(251,191,36,0.45)" />
      <SonarRing delay={600} maxRadius={160} color="rgba(251,191,36,0.35)" />
      <SonarRing delay={1200} maxRadius={160} color="rgba(251,191,36,0.25)" />
      <SonarRing delay={1800} maxRadius={160} color="rgba(251,191,36,0.18)" />

      {/* Amber central orb */}
      <AmberOrb />

      {/* Mist strips at bottom */}
      {mistStrips.map((m, i) => (
        <MistStrip key={i} y={m.y} delay={m.delay} width={m.width} />
      ))}

      {/* Text */}
      <WaitingText />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "#0D1812",
    zIndex: 160,
  },
  sonarRing: {
    position: "absolute",
    borderWidth: 1.5,
  },
  textBlock: {
    position: "absolute",
    bottom: H * 0.18,
    left: 32,
    right: 32,
    alignItems: "center",
  },
  titleText: {
    color: "#F5E6C8",
    fontSize: 21,
    fontWeight: "700",
    textAlign: "center",
    letterSpacing: 0.2,
    textShadowColor: "rgba(251,191,36,0.4)",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
    marginBottom: 8,
  },
  subtitleText: {
    color: "rgba(196,184,154,0.75)",
    fontSize: 14,
    fontStyle: "italic",
    textAlign: "center",
    marginBottom: 18,
  },
  dotsRow: {
    flexDirection: "row",
    gap: 10,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "rgba(251,191,36,0.75)",
  },
});
