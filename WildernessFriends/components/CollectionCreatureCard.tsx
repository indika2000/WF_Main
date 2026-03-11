import React, { useState } from "react";
import { View, Text, Image, StyleSheet, Dimensions, TouchableOpacity } from "react-native";
import type { CreatureCard } from "../types";
import { getImageFileUrl } from "../services/images";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const CARD_WIDTH = (SCREEN_WIDTH - 48 - 12) / 2; // 24px padding each side + 12px gap
const CARD_HEIGHT = CARD_WIDTH * (4 / 3);

const RARITY_COLORS: Record<string, string> = {
  COMMON: "#9CA3AF",
  UNCOMMON: "#34D399",
  RARE: "#60A5FA",
  EPIC: "#A78BFA",
  LEGENDARY: "#FBBF24",
};

interface CollectionCreatureCardProps {
  creature: CreatureCard;
  count?: number;
  onPress?: () => void;
}

export default function CollectionCreatureCard({
  creature,
  count,
  onPress,
}: CollectionCreatureCardProps) {
  const [imageError, setImageError] = useState(false);
  const rarityColor =
    RARITY_COLORS[creature.classification.rarity] || "#9CA3AF";

  const cardImageId = creature.images?.card;
  const hasGeneratedImage = !!cardImageId && !imageError;
  const imageSource = hasGeneratedImage
    ? { uri: getImageFileUrl(cardImageId!) }
    : require("../assets/images/card_designs/test_painted_character.png");

  return (
    <TouchableOpacity
      style={[styles.card, { borderColor: rarityColor + "40" }]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      {/* Creature Image */}
      <View style={styles.imageContainer}>
        <Image
          source={imageSource}
          style={styles.image}
          resizeMode="cover"
          onError={() => setImageError(true)}
        />
        {/* Rarity badge overlay */}
        <View
          style={[
            styles.rarityBadge,
            { backgroundColor: rarityColor + "CC" },
          ]}
        >
          <Text style={styles.rarityText}>
            {creature.classification.rarity}
          </Text>
        </View>
        {/* Duplicate count badge */}
        {count != null && count > 1 && (
          <View style={styles.countBadge}>
            <Text style={styles.countText}>×{count}</Text>
          </View>
        )}
      </View>

      {/* Info */}
      <View style={styles.info}>
        <Text style={styles.name} numberOfLines={1}>
          {creature.presentation.name}
        </Text>
        <Text style={styles.biome} numberOfLines={1}>
          {creature.classification.biome.replace(/_/g, " ")}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    backgroundColor: "#F5F0E8",
    borderRadius: 12,
    borderWidth: 2,
    overflow: "hidden",
  },
  imageContainer: {
    flex: 1,
    backgroundColor: "#E8E0D4",
  },
  image: {
    width: "100%",
    height: "100%",
  },
  rarityBadge: {
    position: "absolute",
    top: 6,
    right: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  rarityText: {
    color: "#fff",
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
  countBadge: {
    position: "absolute",
    top: 6,
    left: 6,
    backgroundColor: "rgba(59,47,47,0.85)",
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 8,
  },
  countText: {
    color: "#F5E6C8",
    fontSize: 11,
    fontWeight: "800",
  },
  info: {
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
  name: {
    color: "#3B2F2F",
    fontSize: 12,
    fontWeight: "700",
  },
  biome: {
    color: "#9A8D82",
    fontSize: 10,
    textTransform: "capitalize",
    marginTop: 1,
  },
});
