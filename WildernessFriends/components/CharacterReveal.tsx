import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ImageBackground,
  StyleSheet,
  Dimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  Easing,
} from "react-native-reanimated";
import LayeredFlipCard from "./LayeredFlipCard";
import CardShimmer, { ShimmerRarity } from "./CardShimmer";
import type { CreatureCard } from "../types";
import { getImageFileUrl } from "../services/images";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");

// Card dimensions — same ratio as dev-tools card-layer-test
const CARD_W = Math.min(SCREEN_WIDTH * 0.72, 290);
const CARD_H = CARD_W * 1.5;

const RARITY_COLORS: Record<string, string> = {
  COMMON: "#9CA3AF",
  UNCOMMON: "#34D399",
  RARE: "#60A5FA",
  EPIC: "#A78BFA",
  LEGENDARY: "#FBBF24",
};

// Maps rarity → card layer assets + shimmer tier
const RARITY_ASSETS: Record<
  string,
  { base: any; border: any; shimmer: ShimmerRarity; lightText: boolean }
> = {
  COMMON: {
    base: require("../assets/images/card_designs/card_backing-normal.png"),
    border: require("../assets/images/card_designs/border_1_transparent.png"),
    shimmer: "common",
    lightText: false,
  },
  UNCOMMON: {
    base: require("../assets/images/card_designs/card_backing_uncommon.png"),
    border: require("../assets/images/card_designs/border_2_transparent.png"),
    shimmer: "uncommon",
    lightText: false,
  },
  RARE: {
    base: require("../assets/images/card_designs/card_backing_rare.png"),
    border: require("../assets/images/card_designs/border_3_transparent.png"),
    shimmer: "rare",
    lightText: true,
  },
  EPIC: {
    base: require("../assets/images/card_designs/card_backing_rare.png"),
    border: require("../assets/images/card_designs/border_4_transparent.png"),
    shimmer: "epic",
    lightText: true,
  },
  LEGENDARY: {
    base: require("../assets/images/card_designs/card_backing_rare.png"),
    border: require("../assets/images/card_designs/border_4_transparent.png"),
    shimmer: "legendary",
    lightText: true,
  },
};

const FALLBACK_ASSETS = RARITY_ASSETS.COMMON;

interface CharacterRevealProps {
  creature: CreatureCard;
  isNewDiscovery: boolean;
  isClaimedVariant: boolean;
  onDismiss: () => void;
  cardImageId?: string | null;
}

function StatPill({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.statPill}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

export default function CharacterReveal({
  creature,
  isNewDiscovery,
  isClaimedVariant,
  onDismiss,
  cardImageId,
}: CharacterRevealProps) {
  const [isFlipped, setIsFlipped] = useState(false);
  const [showInfo, setShowInfo] = useState(false);

  // Info panel slides up after flip completes
  const infoTranslate = useSharedValue(200);
  const infoOpacity = useSharedValue(0);
  // Hint text fades out on flip
  const hintOpacity = useSharedValue(1);

  useEffect(() => {
    if (!isFlipped) return;
    // Fade out the hint
    hintOpacity.value = withTiming(0, { duration: 400, easing: Easing.out(Easing.ease) });
    // After flip duration (800ms), slide up info panel
    const timer = setTimeout(() => {
      setShowInfo(true);
      infoTranslate.value = withTiming(0, {
        duration: 450,
        easing: Easing.out(Easing.cubic),
      });
      infoOpacity.value = withTiming(1, { duration: 400 });
    }, 700);
    return () => clearTimeout(timer);
  }, [isFlipped]);

  const infoPanelStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: infoTranslate.value }],
    opacity: infoOpacity.value,
  }));

  const hintStyle = useAnimatedStyle(() => ({
    opacity: hintOpacity.value,
  }));

  if (!creature) return null;

  const rarity = creature.classification.rarity;
  const assets = RARITY_ASSETS[rarity] ?? FALLBACK_ASSETS;
  const rarityColor = RARITY_COLORS[rarity] || "#9CA3AF";

  // Character image: generated card art, or placeholder while loading
  const characterImage = cardImageId
    ? { uri: getImageFileUrl(cardImageId) }
    : require("../assets/images/card_designs/test_painted_character.png");

  return (
    <View style={styles.container}>
      <ImageBackground
        source={require("../assets/images/character_creator/Character_Reveal.png")}
        style={styles.background}
        resizeMode="cover"
      >
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.content}>

            {/* Card + shimmer, tap to flip */}
            <TouchableOpacity
              activeOpacity={0.92}
              onPress={() => !isFlipped && setIsFlipped(true)}
              style={styles.cardWrapper}
            >
              <View style={{ width: CARD_W, height: CARD_H }}>
                <LayeredFlipCard
                  isFlipped={isFlipped}
                  baseImage={assets.base}
                  characterImage={characterImage}
                  borderImage={assets.border}
                  backImage={require("../assets/images/card_designs/card-back.png")}
                  lightText={assets.lightText}
                  width={CARD_W}
                  height={CARD_H}
                  duration={800}
                />
                {/* Shimmer sits on top of the card, clips to card bounds */}
                <View
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: CARD_W,
                    height: CARD_H,
                  }}
                  pointerEvents="none"
                >
                  <CardShimmer rarity={assets.shimmer} width={CARD_W} height={CARD_H} />
                </View>
              </View>
            </TouchableOpacity>

            {/* Tap hint — fades out after flip */}
            <Animated.Text style={[styles.hintText, hintStyle]}>
              Tap to reveal
            </Animated.Text>

            {/* Info panel — slides up after flip */}
            {showInfo && (
              <Animated.View style={[styles.infoPanel, infoPanelStyle]}>
                {/* Rarity badge */}
                <View
                  style={[
                    styles.rarityBadge,
                    { backgroundColor: rarityColor + "28" },
                  ]}
                >
                  <Text style={[styles.rarityText, { color: rarityColor }]}>
                    {rarity}
                  </Text>
                </View>

                {/* Name + title */}
                <Text style={styles.creatureName}>
                  {creature.presentation.name}
                </Text>
                <Text style={styles.creatureTitle}>
                  {creature.presentation.title}
                </Text>

                {/* Stats */}
                <View style={styles.statsRow}>
                  <StatPill label="POW" value={creature.attributes.power} />
                  <StatPill label="DEF" value={creature.attributes.defense} />
                  <StatPill label="AGI" value={creature.attributes.agility} />
                  <StatPill label="WIS" value={creature.attributes.wisdom} />
                  <StatPill label="FER" value={creature.attributes.ferocity} />
                  <StatPill label="MAG" value={creature.attributes.magic} />
                  <StatPill label="LCK" value={creature.attributes.luck} />
                </View>

                {/* Status badges */}
                {(isNewDiscovery || isClaimedVariant) && (
                  <View style={styles.badgesRow}>
                    {isNewDiscovery && (
                      <View
                        style={[
                          styles.statusBadge,
                          { backgroundColor: "rgba(123,143,107,0.3)" },
                        ]}
                      >
                        <Text
                          style={[
                            styles.statusBadgeText,
                            { color: "#9AAD8A" },
                          ]}
                        >
                          New Discovery
                        </Text>
                      </View>
                    )}
                    {isClaimedVariant && (
                      <View
                        style={[
                          styles.statusBadge,
                          { backgroundColor: "rgba(251,191,36,0.2)" },
                        ]}
                      >
                        <Text
                          style={[
                            styles.statusBadgeText,
                            { color: "#FBBF24" },
                          ]}
                        >
                          Claimed Variant
                        </Text>
                      </View>
                    )}
                  </View>
                )}

                {/* Biome / element line */}
                <Text style={styles.classificationText}>
                  {creature.classification.biome.replace(/_/g, " ")}
                  {" · "}
                  {creature.classification.element.replace(/_/g, " ")}
                </Text>

                {/* Add to Collection button */}
                <TouchableOpacity style={styles.dismissButton} onPress={onDismiss}>
                  <Text style={styles.dismissButtonText}>Add to Collection</Text>
                </TouchableOpacity>
              </Animated.View>
            )}
          </View>
        </SafeAreaView>
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 200,
  },
  background: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
  },
  content: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingBottom: 24,
  },
  cardWrapper: {
    // Shadow for the card
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.45,
    shadowRadius: 16,
    elevation: 12,
  },
  hintText: {
    color: "rgba(245,230,200,0.7)",
    fontSize: 14,
    fontStyle: "italic",
    marginTop: 14,
    textShadowColor: "rgba(0,0,0,0.5)",
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
  infoPanel: {
    width: SCREEN_WIDTH * 0.88,
    backgroundColor: "rgba(15,26,20,0.88)",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "rgba(196,184,154,0.25)",
    paddingVertical: 18,
    paddingHorizontal: 20,
    alignItems: "center",
    marginTop: 14,
  },
  rarityBadge: {
    paddingHorizontal: 16,
    paddingVertical: 5,
    borderRadius: 20,
    marginBottom: 8,
  },
  rarityText: {
    fontSize: 13,
    fontWeight: "800",
    letterSpacing: 1.2,
  },
  creatureName: {
    color: "#F5E6C8",
    fontSize: 22,
    fontWeight: "bold",
    textAlign: "center",
    marginBottom: 3,
  },
  creatureTitle: {
    color: "#C4B89A",
    fontSize: 13,
    fontStyle: "italic",
    textAlign: "center",
    marginBottom: 14,
  },
  statsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 5,
    marginBottom: 12,
  },
  statPill: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.08)",
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 10,
    gap: 3,
  },
  statLabel: {
    color: "#C4B89A",
    fontSize: 9,
    fontWeight: "600",
  },
  statValue: {
    color: "#F5E6C8",
    fontSize: 11,
    fontWeight: "bold",
  },
  badgesRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 10,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusBadgeText: {
    fontSize: 11,
    fontWeight: "600",
  },
  classificationText: {
    color: "#C4B89A",
    fontSize: 12,
    textTransform: "capitalize",
    marginBottom: 16,
  },
  dismissButton: {
    backgroundColor: "#7B8F6B",
    paddingHorizontal: 36,
    paddingVertical: 13,
    borderRadius: 12,
    minWidth: 200,
    alignItems: "center",
  },
  dismissButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
});
