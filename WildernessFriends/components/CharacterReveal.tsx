import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  ImageBackground,
  StyleSheet,
  ScrollView,
  Dimensions,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { CreatureCard } from "../types";
import { getImageFileUrl } from "../services/images";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const IMAGE_WIDTH = SCREEN_WIDTH * 0.75;
const IMAGE_HEIGHT = IMAGE_WIDTH * 1.2; // Portrait aspect ratio for full character

const RARITY_COLORS: Record<string, string> = {
  COMMON: "#9CA3AF",
  UNCOMMON: "#34D399",
  RARE: "#60A5FA",
  EPIC: "#A78BFA",
  LEGENDARY: "#FBBF24",
};

interface CharacterRevealProps {
  creature: CreatureCard;
  isNewDiscovery: boolean;
  isClaimedVariant: boolean;
  onDismiss: () => void;
  cardImageId?: string | null;
}

/**
 * Simulates a gradient fade using layered semi-transparent views.
 * Each strip has increasing opacity toward the edge.
 */
function FadeEdge({
  side,
  color = "rgba(200,190,175,",
}: {
  side: "top" | "bottom" | "left" | "right";
  color?: string;
}) {
  const STRIPS = 5;
  const TOTAL_SIZE = 30;
  const stripSize = TOTAL_SIZE / STRIPS;
  const isHorizontal = side === "left" || side === "right";

  return (
    <View
      style={[
        styles.fadeEdge,
        isHorizontal
          ? { width: TOTAL_SIZE, top: 0, bottom: 0, [side]: 0 }
          : { height: TOTAL_SIZE, left: 0, right: 0, [side]: 0 },
        isHorizontal ? { flexDirection: "row" } : { flexDirection: "column" },
      ]}
      pointerEvents="none"
    >
      {Array.from({ length: STRIPS }).map((_, i) => {
        // Opacity increases toward the edge
        const fromEdge = side === "right" || side === "bottom" ? i : STRIPS - 1 - i;
        const opacity = (fromEdge + 1) / STRIPS * 0.85;
        return (
          <View
            key={i}
            style={[
              isHorizontal
                ? { width: stripSize, height: "100%" as any }
                : { height: stripSize, width: "100%" as any },
              { backgroundColor: `${color}${opacity})` },
            ]}
          />
        );
      })}
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
  const [imageLoading, setImageLoading] = useState(!!cardImageId);
  const [imageError, setImageError] = useState(false);

  if (!creature) return null;

  const rarityColor = RARITY_COLORS[creature.classification.rarity] || "#9CA3AF";

  // Use generated image if available, otherwise placeholder
  const hasGeneratedImage = !!cardImageId && !imageError;
  const imageSource = hasGeneratedImage
    ? { uri: getImageFileUrl(cardImageId!) }
    : require("../assets/images/card_designs/test_painted_character.png");

  return (
    <View style={styles.container}>
      <ImageBackground
        source={require("../assets/images/character_creator/Character_Reveal.png")}
        style={styles.background}
        resizeMode="cover"
      >
        <SafeAreaView style={styles.content}>
          <ScrollView
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {/* Character Image with soft edge fade */}
            <View style={styles.imageContainer}>
              {/* Loading overlay while image fetches */}
              {imageLoading && (
                <View style={styles.imageLoadingOverlay}>
                  <ActivityIndicator size="large" color="#F5E6C8" />
                  <Text style={styles.imageLoadingText}>Painting...</Text>
                </View>
              )}
              <Image
                source={imageSource}
                style={styles.characterImage}
                resizeMode="contain"
                onLoadEnd={() => setImageLoading(false)}
                onError={() => {
                  setImageError(true);
                  setImageLoading(false);
                }}
              />
              {/* Soft gradient-like edge fades */}
              <FadeEdge side="top" />
              <FadeEdge side="bottom" />
              <FadeEdge side="left" />
              <FadeEdge side="right" />
            </View>

            {/* Text Panel */}
            <ImageBackground
              source={require("../assets/images/character_creator/Character_Creator_Text_Panel.png")}
              style={styles.textPanel}
              resizeMode="stretch"
            >
              <View style={styles.textPanelContent}>
                {/* Rarity Badge */}
                <View
                  style={[
                    styles.rarityBadge,
                    { backgroundColor: rarityColor + "30" },
                  ]}
                >
                  <Text style={[styles.rarityText, { color: rarityColor }]}>
                    {creature.classification.rarity}
                  </Text>
                </View>

                {/* Name */}
                <Text style={styles.creatureName}>
                  {creature.presentation.name}
                </Text>

                {/* Title */}
                <Text style={styles.creatureTitle}>
                  {creature.presentation.title}
                </Text>

                {/* Stats Row */}
                <View style={styles.statsRow}>
                  <StatPill label="POW" value={creature.attributes.power} />
                  <StatPill label="DEF" value={creature.attributes.defense} />
                  <StatPill label="AGI" value={creature.attributes.agility} />
                  <StatPill label="WIS" value={creature.attributes.wisdom} />
                  <StatPill label="FER" value={creature.attributes.ferocity} />
                  <StatPill label="MAG" value={creature.attributes.magic} />
                  <StatPill label="LCK" value={creature.attributes.luck} />
                </View>

                {/* Status Badges */}
                <View style={styles.badgesRow}>
                  {isNewDiscovery && (
                    <View style={[styles.statusBadge, { backgroundColor: "rgba(123,143,107,0.3)" }]}>
                      <Text style={[styles.statusBadgeText, { color: "#9AAD8A" }]}>
                        New Discovery
                      </Text>
                    </View>
                  )}
                  {isClaimedVariant && (
                    <View style={[styles.statusBadge, { backgroundColor: "rgba(251,191,36,0.2)" }]}>
                      <Text style={[styles.statusBadgeText, { color: "#FBBF24" }]}>
                        Claimed Variant
                      </Text>
                    </View>
                  )}
                </View>

                {/* Classification Info */}
                <View style={styles.classificationRow}>
                  <Text style={styles.classificationText}>
                    {creature.classification.biome.replace(/_/g, " ")} · {creature.classification.family.replace(/_/g, " ")}
                  </Text>
                  <Text style={styles.classificationText}>
                    {creature.classification.element.replace(/_/g, " ")} · {creature.classification.size}
                  </Text>
                </View>

                {/* Dismiss Button */}
                <TouchableOpacity style={styles.dismissButton} onPress={onDismiss}>
                  <Text style={styles.dismissButtonText}>Add to Collection</Text>
                </TouchableOpacity>
              </View>
            </ImageBackground>
          </ScrollView>
        </SafeAreaView>
      </ImageBackground>
    </View>
  );
}

function StatPill({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.statPill}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
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
  content: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 20,
  },
  imageContainer: {
    width: IMAGE_WIDTH,
    height: IMAGE_HEIGHT,
    borderRadius: 16,
    overflow: "hidden",
    marginBottom: -10,
    zIndex: 1,
  },
  characterImage: {
    width: "100%",
    height: "100%",
  },
  fadeEdge: {
    position: "absolute",
    zIndex: 2,
  },
  imageLoadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 3,
    backgroundColor: "rgba(30,30,30,0.6)",
    justifyContent: "center",
    alignItems: "center",
  },
  imageLoadingText: {
    color: "#F5E6C8",
    fontSize: 14,
    fontStyle: "italic",
    marginTop: 8,
  },
  textPanel: {
    width: SCREEN_WIDTH * 0.9,
    minHeight: 320,
    paddingTop: 30,
  },
  textPanelContent: {
    padding: 24,
    alignItems: "center",
  },
  rarityBadge: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    marginBottom: 8,
  },
  rarityText: {
    fontSize: 14,
    fontWeight: "800",
    letterSpacing: 1,
  },
  creatureName: {
    color: "#F5E6C8",
    fontSize: 24,
    fontWeight: "bold",
    textAlign: "center",
    marginBottom: 4,
  },
  creatureTitle: {
    color: "#C4B89A",
    fontSize: 14,
    fontStyle: "italic",
    textAlign: "center",
    marginBottom: 16,
  },
  statsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 6,
    marginBottom: 12,
  },
  statPill: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.1)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
    gap: 4,
  },
  statLabel: {
    color: "#C4B89A",
    fontSize: 10,
    fontWeight: "600",
  },
  statValue: {
    color: "#F5E6C8",
    fontSize: 12,
    fontWeight: "bold",
  },
  badgesRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 12,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusBadgeText: {
    fontSize: 12,
    fontWeight: "600",
  },
  classificationRow: {
    alignItems: "center",
    marginBottom: 16,
  },
  classificationText: {
    color: "#C4B89A",
    fontSize: 12,
    textTransform: "capitalize",
  },
  dismissButton: {
    backgroundColor: "#7B8F6B",
    paddingHorizontal: 32,
    paddingVertical: 14,
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
