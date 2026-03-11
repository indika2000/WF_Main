import React, { useState } from "react";
import {
  View,
  Text,
  Image,
  Modal,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Dimensions,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { CreatureCard } from "../types";
import { getImageFileUrl } from "../services/images";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const IMAGE_SIZE = SCREEN_WIDTH - 48;

const RARITY_COLORS: Record<string, string> = {
  COMMON: "#9CA3AF",
  UNCOMMON: "#34D399",
  RARE: "#60A5FA",
  EPIC: "#A78BFA",
  LEGENDARY: "#FBBF24",
};

interface CreatureDetailModalProps {
  creature: CreatureCard | null;
  visible: boolean;
  onClose: () => void;
}

function ImageWithLoader({
  imageId,
  label,
  size,
  aspectRatio,
}: {
  imageId: string | undefined;
  label: string;
  size: number;
  aspectRatio: number;
}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  if (!imageId) {
    return (
      <View style={styles.imageSection}>
        <Text style={styles.imageLabel}>{label}</Text>
        <View
          style={[
            styles.placeholder,
            { width: size, height: size * aspectRatio },
          ]}
        >
          <Text style={styles.placeholderText}>Not generated</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.imageSection}>
      <Text style={styles.imageLabel}>{label}</Text>
      <View style={{ width: size, height: size * aspectRatio }}>
        {loading && (
          <View style={[styles.placeholder, { width: size, height: size * aspectRatio, position: "absolute", zIndex: 1 }]}>
            <ActivityIndicator color="#7B8F6B" />
          </View>
        )}
        {!error ? (
          <Image
            source={{ uri: getImageFileUrl(imageId) }}
            style={{ width: size, height: size * aspectRatio, borderRadius: 12 }}
            resizeMode="contain"
            onLoadEnd={() => setLoading(false)}
            onError={() => {
              setError(true);
              setLoading(false);
            }}
          />
        ) : (
          <View
            style={[
              styles.placeholder,
              { width: size, height: size * aspectRatio },
            ]}
          >
            <Text style={styles.placeholderText}>Failed to load</Text>
          </View>
        )}
      </View>
    </View>
  );
}

export default function CreatureDetailModal({
  creature,
  visible,
  onClose,
}: CreatureDetailModalProps) {
  if (!creature) return null;

  const rarityColor =
    RARITY_COLORS[creature.classification.rarity] || "#9CA3AF";

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="fullScreen"
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View style={{ flex: 1 }}>
            <Text style={styles.name}>{creature.presentation.name}</Text>
            <Text style={styles.title}>{creature.presentation.title}</Text>
          </View>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeText}>Close</Text>
          </TouchableOpacity>
        </View>

        {/* Rarity badge */}
        <View style={styles.rarityRow}>
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
          <Text style={styles.artistText}>
            Artist: {creature.images?.artist_id || "unknown"}
          </Text>
        </View>

        {/* Images */}
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          <ImageWithLoader
            imageId={creature.images?.card}
            label="Card (3:4)"
            size={IMAGE_SIZE}
            aspectRatio={4 / 3}
          />

          <ImageWithLoader
            imageId={creature.images?.headshot_color}
            label="Headshot — Color (1:1)"
            size={IMAGE_SIZE * 0.7}
            aspectRatio={1}
          />

          <ImageWithLoader
            imageId={creature.images?.headshot_pencil}
            label="Headshot — Pencil (1:1)"
            size={IMAGE_SIZE * 0.7}
            aspectRatio={1}
          />

          <View style={{ height: 40 }} />
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F0E8",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#E8E0D4",
  },
  name: {
    color: "#3B2F2F",
    fontSize: 20,
    fontWeight: "700",
  },
  title: {
    color: "#9A8D82",
    fontSize: 13,
    fontStyle: "italic",
    marginTop: 2,
  },
  closeButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: "#3B2F2F",
    borderRadius: 8,
  },
  closeText: {
    color: "#F5E6C8",
    fontSize: 14,
    fontWeight: "600",
  },
  rarityRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 8,
    gap: 12,
  },
  rarityBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  rarityText: {
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
  artistText: {
    color: "#9A8D82",
    fontSize: 12,
    textTransform: "capitalize",
  },
  scrollContent: {
    alignItems: "center",
    paddingTop: 16,
  },
  imageSection: {
    alignItems: "center",
    marginBottom: 24,
  },
  imageLabel: {
    color: "#3B2F2F",
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 8,
  },
  placeholder: {
    backgroundColor: "#E8E0D4",
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
  },
  placeholderText: {
    color: "#9A8D82",
    fontSize: 13,
    fontStyle: "italic",
  },
});
