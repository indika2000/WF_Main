import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "expo-router";
import { useAuth } from "../../context/AuthContext";
import * as characterService from "../../services/characters";
import * as permissionsService from "../../services/permissions";
import * as tokenManager from "../../services/tokenManager";
import CreationCameraModal from "../../components/CreationCameraModal";
import PackOpeningVideo from "../../components/PackOpeningVideo";
import CharacterReveal from "../../components/CharacterReveal";
import type {
  GenerateCreatureResponse,
  UsageCheckResponse,
  CollectionResponse,
} from "../../types";

type CreatorState = "idle" | "scanning" | "generating" | "reveal";

const RARITY_COLORS: Record<string, string> = {
  COMMON: "#9CA3AF",
  UNCOMMON: "#34D399",
  RARE: "#60A5FA",
  EPIC: "#A78BFA",
  LEGENDARY: "#FBBF24",
};

export default function CharacterCreatorScreen() {
  const { user, apiReady } = useAuth();
  const [state, setState] = useState<CreatorState>("idle");
  const [usage, setUsage] = useState<UsageCheckResponse | null>(null);
  const [collection, setCollection] = useState<CollectionResponse | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Generation state
  const [videoFinished, setVideoFinished] = useState(false);
  const [creatureResult, setCreatureResult] =
    useState<GenerateCreatureResponse | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [rescanMessage, setRescanMessage] = useState<string | null>(null);
  const [cardImageId, setCardImageId] = useState<string | null>(null);
  const sseAbortRef = useRef<{ abort: () => void } | null>(null);

  const fetchStats = useCallback(async () => {
    if (!apiReady || !user) return;
    setLoadingStats(true);
    try {
      const [usageData, collectionData] = await Promise.all([
        permissionsService.checkUsage(user.uid, "character_creation"),
        characterService.getMyCollection(0, 200),
      ]);
      setUsage(usageData);
      setCollection(collectionData);
    } catch (err: any) {
      setError(err?.message || "Failed to load stats");
    } finally {
      setLoadingStats(false);
    }
  }, [apiReady, user]);

  // Refresh on screen focus
  useFocusEffect(
    useCallback(() => {
      fetchStats();
    }, [fetchStats])
  );

  const handleCreatePress = () => {
    setError(null);
    setRescanMessage(null);
    setState("scanning");
  };

  const handleCameraClose = () => {
    setState("idle");
  };

  const handleCodeScanned = async (codeType: string, rawValue: string) => {
    setState("generating");
    setVideoFinished(false);
    setCreatureResult(null);
    setGenerationError(null);
    setCardImageId(null);

    try {
      const result = await characterService.generateCreature(codeType, rawValue);
      console.log("[CharacterCreator] API result:", JSON.stringify(result, null, 2));
      console.log("[CharacterCreator] creature field:", result?.creature ? "EXISTS" : "MISSING", typeof result?.creature);
      setCreatureResult(result);
    } catch (err: any) {
      console.log("[CharacterCreator] API error:", JSON.stringify(err, null, 2));
      const message =
        err?.message || err?.response?.data?.message || "Generation failed";
      setGenerationError(message);
      // Don't set state to idle here — let the video finish first
    }
  };

  const handleVideoEnd = () => {
    setVideoFinished(true);
  };

  // Transition after both video ends and API completes (success or failure)
  useEffect(() => {
    if (state !== "generating" || !videoFinished) return;
    // Wait for API to finish (either success or error)
    if (!creatureResult && !generationError) return;

    if (creatureResult?.creature) {
      // Check if this was a re-scan (not new discovery, not claimed variant)
      if (!creatureResult.is_new_discovery && !creatureResult.is_claimed_variant) {
        // Re-scan of owned barcode — skip reveal, go back to idle
        setError(null);
        setState("idle");
        // Show a brief message that this creature is already owned
        setRescanMessage(creatureResult.creature.presentation?.name || "This creature");
      } else {
        setState("reveal");
      }
    } else {
      // API failed or creature is missing in response
      setError(generationError || "Creature data missing in response");
      setState("idle");
    }
  }, [state, videoFinished, creatureResult, generationError]);

  // Subscribe to SSE for image readiness when entering reveal state
  useEffect(() => {
    if (state !== "reveal" || !creatureResult?.creature) return;

    const creatureId = creatureResult.creature.identity.creature_id;

    // Check if creature already has a card image from the API response
    const existingCardImage = creatureResult.creature.images?.card;
    if (existingCardImage) {
      setCardImageId(existingCardImage);
      return;
    }

    // Subscribe to SSE for real-time image updates
    (async () => {
      const token = await tokenManager.getToken();
      if (!token) return;

      const sub = characterService.subscribeToImageStream(creatureId, token, {
        onImageReady: (imageType, imageId) => {
          console.log("[SSE] Image ready:", imageType, imageId);
          if (imageType === "card") {
            setCardImageId(imageId);
          }
        },
        onComplete: () => {
          console.log("[SSE] All images complete");
        },
        onError: (err) => {
          console.warn("[SSE] Error:", err);
        },
      });
      sseAbortRef.current = sub;
    })();

    return () => {
      sseAbortRef.current?.abort();
      sseAbortRef.current = null;
    };
  }, [state, creatureResult]);

  const handleRevealDismiss = () => {
    sseAbortRef.current?.abort();
    sseAbortRef.current = null;
    setState("idle");
    setCreatureResult(null);
    setVideoFinished(false);
    setGenerationError(null);
    setCardImageId(null);
    fetchStats();
  };

  const canCreate = usage ? usage.allowed : false;
  const remaining = usage ? usage.remaining : 0;
  const used = usage ? usage.used : 0;
  const limit = usage ? usage.limit : 0;
  const usagePercent = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;

  // Compute rarity distribution from collection
  const rarityDistribution = computeRarityDistribution(collection);
  const totalCreatures = collection?.total || 0;

  return (
    <SafeAreaView className="flex-1 bg-primary">
      {/* Idle + Stats View */}
      <ScrollView className="flex-1 px-6 py-4">
        {/* Header */}
        <Text className="text-bark-dark text-2xl font-bold mb-1">
          Character Creator
        </Text>
        <Text className="text-text-muted text-sm mb-6">
          Scan barcodes to discover creatures
        </Text>

        {/* Usage Bar */}
        <View className="bg-secondary rounded-xl p-4 mb-4">
          <View className="flex-row justify-between mb-2">
            <Text className="text-text-secondary text-sm font-semibold">
              Monthly Creations
            </Text>
            <Text className="text-text-muted text-sm">
              {used} / {limit}
            </Text>
          </View>
          <View style={styles.usageBarBg}>
            <View
              style={[
                styles.usageBarFill,
                {
                  width: `${usagePercent}%` as any,
                  backgroundColor: usagePercent >= 100 ? "#C45A4A" : "#7B8F6B",
                },
              ]}
            />
          </View>
          {remaining > 0 ? (
            <Text className="text-text-muted text-xs mt-1">
              {remaining} creation{remaining !== 1 ? "s" : ""} remaining this
              month
            </Text>
          ) : (
            <Text className="text-error text-xs mt-1">
              Monthly limit reached
            </Text>
          )}
        </View>

        {/* Collection Stats */}
        <View className="bg-secondary rounded-xl p-4 mb-4">
          <Text className="text-text-secondary text-sm font-semibold mb-3">
            Collection Stats
          </Text>
          {loadingStats ? (
            <ActivityIndicator size="small" color="#7B8F6B" />
          ) : (
            <>
              <View className="flex-row justify-between mb-2">
                <Text className="text-text-muted text-sm">Total Creatures</Text>
                <Text className="text-text-primary text-sm font-bold">
                  {totalCreatures}
                </Text>
              </View>

              {/* Rarity Distribution */}
              {rarityDistribution.length > 0 && (
                <View className="mt-2">
                  <Text className="text-text-muted text-xs mb-2">
                    Rarity Distribution
                  </Text>
                  <View className="flex-row flex-wrap" style={{ gap: 6 }}>
                    {rarityDistribution.map(({ rarity, count }) => (
                      <View
                        key={rarity}
                        style={[
                          styles.rarityPill,
                          {
                            backgroundColor:
                              (RARITY_COLORS[rarity] || "#9CA3AF") + "20",
                          },
                        ]}
                      >
                        <Text
                          style={[
                            styles.rarityPillText,
                            { color: RARITY_COLORS[rarity] || "#9CA3AF" },
                          ]}
                        >
                          {rarity} x{count}
                        </Text>
                      </View>
                    ))}
                  </View>
                </View>
              )}
            </>
          )}
        </View>

        {/* Rescan Notice */}
        {rescanMessage && (
          <View className="bg-secondary rounded-xl p-3 mb-4 border border-parchment-dark">
            <Text className="text-text-secondary text-sm font-semibold">
              Already in Collection
            </Text>
            <Text className="text-text-muted text-xs mt-1">
              "{rescanMessage}" is already yours — no usage consumed
            </Text>
          </View>
        )}

        {/* Error */}
        {error && (
          <View className="bg-parchment rounded-xl p-3 mb-4 border border-parchment-dark">
            <Text className="text-error text-sm">{error}</Text>
          </View>
        )}

        {/* Create Button */}
        <TouchableOpacity
          style={[
            styles.createButton,
            !canCreate && styles.createButtonDisabled,
          ]}
          onPress={handleCreatePress}
          disabled={!canCreate || !apiReady}
          activeOpacity={0.8}
        >
          <Text style={styles.createButtonText}>
            {!apiReady
              ? "Connecting..."
              : !canCreate
                ? "Limit Reached"
                : "Create New Character"}
          </Text>
          {canCreate && apiReady && (
            <Text style={styles.createButtonSubtext}>
              {remaining} remaining
            </Text>
          )}
        </TouchableOpacity>

        <View className="h-8" />
      </ScrollView>

      {/* Camera Modal */}
      <CreationCameraModal
        visible={state === "scanning"}
        onClose={handleCameraClose}
        onCodeScanned={handleCodeScanned}
      />

      {/* Pack Opening Video */}
      <PackOpeningVideo
        visible={state === "generating"}
        onVideoEnd={handleVideoEnd}
        showLoadingIndicator={videoFinished && !creatureResult && !generationError}
      />

      {/* Character Reveal */}
      {state === "reveal" && creatureResult && (
        <CharacterReveal
          creature={creatureResult.creature}
          isNewDiscovery={creatureResult.is_new_discovery}
          isClaimedVariant={creatureResult.is_claimed_variant}
          onDismiss={handleRevealDismiss}
          cardImageId={cardImageId}
        />
      )}
    </SafeAreaView>
  );
}

function computeRarityDistribution(
  collection: CollectionResponse | null
): Array<{ rarity: string; count: number }> {
  if (!collection || collection.items.length === 0) return [];

  const counts: Record<string, number> = {};
  for (const item of collection.items) {
    const rarity = item.creature?.classification?.rarity || "UNKNOWN";
    counts[rarity] = (counts[rarity] || 0) + 1;
  }

  const order = ["LEGENDARY", "EPIC", "RARE", "UNCOMMON", "COMMON"];
  return Object.entries(counts)
    .sort(([a], [b]) => {
      const ai = order.indexOf(a);
      const bi = order.indexOf(b);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    })
    .map(([rarity, count]) => ({ rarity, count }));
}

const styles = StyleSheet.create({
  usageBarBg: {
    height: 8,
    backgroundColor: "#E8E0D4",
    borderRadius: 4,
    overflow: "hidden",
  },
  usageBarFill: {
    height: "100%",
    borderRadius: 4,
  },
  rarityPill: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
  },
  rarityPillText: {
    fontSize: 11,
    fontWeight: "700",
  },
  createButton: {
    backgroundColor: "#7B8F6B",
    paddingVertical: 18,
    borderRadius: 16,
    alignItems: "center",
  },
  createButtonDisabled: {
    backgroundColor: "#D4CFC7",
  },
  createButtonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },
  createButtonSubtext: {
    color: "rgba(255,255,255,0.7)",
    fontSize: 12,
    marginTop: 2,
  },
});
