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

const ORBIT_RADIUS_OUTER = 110;
const ORBIT_RADIUS_INNER = 72;
const SPARKLE_COUNT = 8;
const INNER_RUNE_COUNT = 6;

interface Props {
  visible: boolean;
  onComplete: () => void;
}

// A single orbiting sparkle — positioned by its parent container rotating
function Sparkle({
  angle,
  radius,
  size,
  color,
  delay,
}: {
  angle: number;
  radius: number;
  size: number;
  color: string;
  delay: number;
}) {
  const pulse = useSharedValue(0);

  useEffect(() => {
    pulse.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(1, { duration: 800, easing: Easing.out(Easing.quad) }),
          withTiming(0.3, { duration: 900, easing: Easing.inOut(Easing.ease) }),
          withTiming(1, { duration: 700, easing: Easing.in(Easing.quad) }),
        ),
        -1,
        false
      )
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    opacity: pulse.value,
    transform: [{ scale: interpolate(pulse.value, [0.3, 1], [0.5, 1.3]) }],
  }));

  const x = Math.cos(angle) * radius;
  const y = Math.sin(angle) * radius;

  return (
    <Animated.View
      style={[
        {
          position: "absolute",
          left: W / 2 + x - size,
          top: H / 2 + y - size,
          width: size * 2,
          height: size * 2,
          borderRadius: size,
          backgroundColor: color,
        },
        style,
      ]}
      pointerEvents="none"
    >
      {/* Bright center */}
      <View
        style={{
          position: "absolute",
          left: size * 0.35,
          top: size * 0.35,
          width: size * 0.6,
          height: size * 0.6,
          borderRadius: size * 0.3,
          backgroundColor: "rgba(255,255,255,0.9)",
        }}
      />
    </Animated.View>
  );
}

// Rotating rune ring
function RuneRing({
  radius,
  speed,
  reverse,
  color,
  dashes,
}: {
  radius: number;
  speed: number;
  reverse: boolean;
  color: string;
  dashes: number;
}) {
  const rotation = useSharedValue(0);

  useEffect(() => {
    rotation.value = withRepeat(
      withTiming(reverse ? -360 : 360, {
        duration: speed,
        easing: Easing.linear,
      }),
      -1,
      false
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
  }));

  const segments = Array.from({ length: dashes });
  const segAngle = 360 / dashes;

  return (
    <Animated.View
      style={[
        {
          position: "absolute",
          width: radius * 2,
          height: radius * 2,
          left: W / 2 - radius,
          top: H / 2 - radius,
        },
        style,
      ]}
      pointerEvents="none"
    >
      {segments.map((_, i) => (
        <View
          key={i}
          style={{
            position: "absolute",
            left: radius - 1,
            top: 0,
            width: 2,
            height: 10,
            backgroundColor: color,
            borderRadius: 1,
            transformOrigin: `1px ${radius}px`,
            transform: [{ rotate: `${i * segAngle}deg` }] as any,
          }}
        />
      ))}
    </Animated.View>
  );
}

// Pulsing central glow orb
function CentralOrb() {
  const scale = useSharedValue(1);
  const opacity = useSharedValue(0.6);

  useEffect(() => {
    scale.value = withRepeat(
      withSequence(
        withTiming(1.15, { duration: 1400, easing: Easing.inOut(Easing.ease) }),
        withTiming(0.92, { duration: 1200, easing: Easing.inOut(Easing.ease) }),
      ),
      -1,
      true
    );
    opacity.value = withRepeat(
      withSequence(
        withTiming(0.9, { duration: 1400, easing: Easing.inOut(Easing.ease) }),
        withTiming(0.45, { duration: 1200, easing: Easing.inOut(Easing.ease) }),
      ),
      -1,
      true
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  const ORB_SIZE = 54;

  return (
    <Animated.View
      style={[
        {
          position: "absolute",
          width: ORB_SIZE,
          height: ORB_SIZE,
          borderRadius: ORB_SIZE / 2,
          left: W / 2 - ORB_SIZE / 2,
          top: H / 2 - ORB_SIZE / 2,
          backgroundColor: "rgba(180,220,160,0.25)",
          borderWidth: 1.5,
          borderColor: "rgba(139,177,116,0.7)",
        },
        style,
      ]}
      pointerEvents="none"
    >
      {/* Inner bright core */}
      <View
        style={{
          position: "absolute",
          width: 20,
          height: 20,
          borderRadius: 10,
          left: 17,
          top: 17,
          backgroundColor: "rgba(200,240,180,0.8)",
        }}
      />
    </Animated.View>
  );
}

// Ambient floating leaf particle
function FloatingLeaf({
  startX,
  startY,
  delay,
}: {
  startX: number;
  startY: number;
  delay: number;
}) {
  const translateY = useSharedValue(0);
  const opacity = useSharedValue(0);
  const rotate = useSharedValue(0);

  useEffect(() => {
    const cycle = () => {
      translateY.value = 0;
      opacity.value = 0;
      rotate.value = 0;

      opacity.value = withDelay(
        delay,
        withSequence(
          withTiming(0.7, { duration: 600 }),
          withTiming(0.7, { duration: 2800 }),
          withTiming(0, { duration: 600 }),
        )
      );
      translateY.value = withDelay(
        delay,
        withTiming(-120, { duration: 4000, easing: Easing.out(Easing.ease) })
      );
      rotate.value = withDelay(
        delay,
        withRepeat(withTiming(360, { duration: 3000, easing: Easing.linear }), 1, false)
      );
    };
    cycle();
    const id = setInterval(cycle, 4000 + delay);
    return () => clearInterval(id);
  }, []);

  const style = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [
      { translateY: translateY.value },
      { rotate: `${rotate.value}deg` },
    ],
  }));

  return (
    <Animated.View
      style={[
        {
          position: "absolute",
          left: startX,
          top: startY,
          width: 6,
          height: 9,
          borderRadius: 3,
          backgroundColor: "rgba(139,177,116,0.6)",
        },
        style,
      ]}
      pointerEvents="none"
    />
  );
}

// Animated title text — letters pulse with staggered glow
function PulsingTitle() {
  const glow = useSharedValue(0);

  useEffect(() => {
    glow.value = withRepeat(
      withSequence(
        withTiming(1, { duration: 1200, easing: Easing.inOut(Easing.ease) }),
        withTiming(0.4, { duration: 1000, easing: Easing.inOut(Easing.ease) }),
      ),
      -1,
      true
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    opacity: interpolate(glow.value, [0, 1], [0.7, 1]),
    textShadowRadius: interpolate(glow.value, [0, 1], [4, 12]),
  }));

  return (
    <Animated.Text style={[styles.titleText, style]}>
      We're finding your creature!
    </Animated.Text>
  );
}

// Animated ellipsis dots
function BouncingDots() {
  const delays = [0, 200, 400];
  return (
    <View style={styles.dotsRow}>
      {delays.map((delay, i) => (
        <BounceDot key={i} delay={delay} />
      ))}
    </View>
  );
}

function BounceDot({ delay }: { delay: number }) {
  const y = useSharedValue(0);

  useEffect(() => {
    y.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(-6, { duration: 350, easing: Easing.out(Easing.quad) }),
          withTiming(0, { duration: 350, easing: Easing.in(Easing.quad) }),
          withTiming(0, { duration: 400 }),
        ),
        -1,
        false
      )
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    transform: [{ translateY: y.value }],
  }));

  return (
    <Animated.View style={[styles.dot, style]} />
  );
}

export default function CreatureSearchAnimation({ visible, onComplete }: Props) {
  // Auto-advance after 5 seconds
  useEffect(() => {
    if (!visible) return;
    const timer = setTimeout(onComplete, 5000);
    return () => clearTimeout(timer);
  }, [visible, onComplete]);

  if (!visible) return null;

  const outerSparkles = Array.from({ length: SPARKLE_COUNT }, (_, i) => ({
    angle: (i / SPARKLE_COUNT) * Math.PI * 2,
    size: 4 + (i % 3) * 1.5,
    color:
      i % 3 === 0
        ? "rgba(251,191,36,0.8)"
        : i % 3 === 1
          ? "rgba(139,177,116,0.9)"
          : "rgba(255,255,255,0.7)",
    delay: i * 180,
  }));

  const innerRunes = Array.from({ length: INNER_RUNE_COUNT }, (_, i) => ({
    angle: (i / INNER_RUNE_COUNT) * Math.PI * 2,
    size: 2.5,
    color: "rgba(139,177,116,0.6)",
    delay: i * 120,
  }));

  const leaves = [
    { startX: W * 0.2, startY: H * 0.65, delay: 0 },
    { startX: W * 0.35, startY: H * 0.7, delay: 700 },
    { startX: W * 0.6, startY: H * 0.62, delay: 1400 },
    { startX: W * 0.75, startY: H * 0.68, delay: 300 },
    { startX: W * 0.15, startY: H * 0.55, delay: 2000 },
    { startX: W * 0.8, startY: H * 0.58, delay: 1100 },
  ];

  return (
    <View style={styles.container} pointerEvents="none">
      {/* Ambient radial glow behind orb */}
      <View style={styles.radialGlow} pointerEvents="none" />

      {/* Outer rune ring — slow clockwise */}
      <RuneRing radius={ORBIT_RADIUS_OUTER} speed={9000} reverse={false} color="rgba(251,191,36,0.35)" dashes={24} />

      {/* Mid rune ring — faster counter-clockwise */}
      <RuneRing radius={ORBIT_RADIUS_INNER} speed={6000} reverse={true} color="rgba(139,177,116,0.5)" dashes={16} />

      {/* Outer orbiting sparkles */}
      {outerSparkles.map((s, i) => (
        <Sparkle
          key={i}
          angle={s.angle}
          radius={ORBIT_RADIUS_OUTER}
          size={s.size}
          color={s.color}
          delay={s.delay}
        />
      ))}

      {/* Inner rune motes */}
      {innerRunes.map((s, i) => (
        <Sparkle
          key={`i${i}`}
          angle={s.angle}
          radius={ORBIT_RADIUS_INNER}
          size={s.size}
          color={s.color}
          delay={s.delay}
        />
      ))}

      {/* Central glow orb */}
      <CentralOrb />

      {/* Floating leaf particles */}
      {leaves.map((l, i) => (
        <FloatingLeaf key={i} startX={l.startX} startY={l.startY} delay={l.delay} />
      ))}

      {/* Text block */}
      <View style={styles.textBlock} pointerEvents="none">
        <PulsingTitle />
        <Text style={styles.subtitleText}>Searching the wilderness...</Text>
        <BouncingDots />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "#0B1410",
    zIndex: 150,
    alignItems: "center",
    justifyContent: "center",
  },
  radialGlow: {
    position: "absolute",
    width: 280,
    height: 280,
    borderRadius: 140,
    left: W / 2 - 140,
    top: H / 2 - 140,
    backgroundColor: "rgba(45,90,69,0.18)",
  },
  textBlock: {
    position: "absolute",
    bottom: H * 0.2,
    left: 32,
    right: 32,
    alignItems: "center",
  },
  titleText: {
    color: "#F5E6C8",
    fontSize: 22,
    fontWeight: "800",
    textAlign: "center",
    letterSpacing: 0.3,
    textShadowColor: "rgba(251,191,36,0.5)",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 8,
    marginBottom: 8,
  },
  subtitleText: {
    color: "rgba(139,177,116,0.8)",
    fontSize: 14,
    fontStyle: "italic",
    textAlign: "center",
    marginBottom: 16,
  },
  dotsRow: {
    flexDirection: "row",
    gap: 8,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: "rgba(139,177,116,0.7)",
  },
});
