import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  TextInput,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  useCodeScanner,
} from "react-native-vision-camera";
import { useAuth } from "../../../context/AuthContext";
import * as characterService from "../../../services/characters";
import type {
  GenerateCreatureResponse,
  SupplyStatus,
  CollectionResponse,
} from "../../../types";

const CODE_TYPES = ["EAN_13", "UPC_A", "QR"];

/** Map Vision Camera code types to our CODE_TYPES */
const CAMERA_TYPE_MAP: Record<string, number> = {
  "ean-13": 0,
  "upc-a": 1,
  "qr": 2,
};

const RARITY_COLORS: Record<string, string> = {
  COMMON: "#9CA3AF",
  UNCOMMON: "#34D399",
  RARE: "#60A5FA",
  EPIC: "#A78BFA",
  LEGENDARY: "#FBBF24",
};

export default function CharacterGenTestScreen() {
  const { apiReady } = useAuth();
  const [codeType, setCodeType] = useState(0);
  const [barcodeValue, setBarcodeValue] = useState("5012345678900");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateCreatureResponse | null>(null);
  const [supply, setSupply] = useState<SupplyStatus | null>(null);
  const [collection, setCollection] = useState<CollectionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scannerOpen, setScannerOpen] = useState(false);

  // Camera setup
  const { hasPermission, requestPermission } = useCameraPermission();
  const device = useCameraDevice("back");

  const codeScanner = useCodeScanner({
    codeTypes: ["qr", "ean-13", "ean-8", "upc-a", "upc-e", "code-128"],
    onCodeScanned: (codes) => {
      if (codes.length > 0 && codes[0].value) {
        const scannedType = codes[0].type;
        const scannedValue = codes[0].value;

        // Map camera type to our code type index
        const typeIndex = CAMERA_TYPE_MAP[scannedType];
        if (typeIndex !== undefined) {
          setCodeType(typeIndex);
        }

        setBarcodeValue(scannedValue);
        setScannerOpen(false);
      }
    },
  });

  const handleGenerate = async () => {
    if (!apiReady) {
      setError("API not connected. Wait for token exchange.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await characterService.generateCreature(
        CODE_TYPES[codeType],
        barcodeValue
      );
      setResult(data);
    } catch (err: any) {
      setError(
        err?.response?.data?.message || err?.message || "Generation failed"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSupply = async () => {
    if (!apiReady) return;
    setLoading(true);
    try {
      const data = await characterService.getSupplyStatus();
      setSupply(data);
    } catch (err: any) {
      setError(err?.message || "Failed to fetch supply");
    } finally {
      setLoading(false);
    }
  };

  const handleCollection = async () => {
    if (!apiReady) return;
    setLoading(true);
    try {
      const data = await characterService.getMyCollection();
      setCollection(data);
    } catch (err: any) {
      setError(err?.message || "Failed to fetch collection");
    } finally {
      setLoading(false);
    }
  };

  const creature = result?.creature;
  const rarityColor = creature
    ? RARITY_COLORS[creature.classification.rarity] || "#9CA3AF"
    : "#9CA3AF";

  return (
    <SafeAreaView className="flex-1 bg-primary" edges={["bottom"]}>
      <ScrollView className="flex-1 px-4 py-2">
        {/* API Status */}
        <Text className="text-text-muted text-xs mb-3">
          {apiReady ? "API Connected" : "API Not Connected"}
        </Text>

        {/* Code Type Picker */}
        <Text className="text-text-secondary text-xs mb-1">Code Type</Text>
        <View className="flex-row gap-2 mb-3">
          {CODE_TYPES.map((ct, i) => (
            <TouchableOpacity
              key={ct}
              onPress={() => setCodeType(i)}
              className={`px-3 py-1.5 rounded-full ${
                codeType === i ? "bg-accent-green" : "bg-secondary"
              }`}
              activeOpacity={0.7}
            >
              <Text
                className={`text-xs font-semibold ${
                  codeType === i ? "text-primary" : "text-text-muted"
                }`}
              >
                {ct}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Barcode Input + Scan Button */}
        <Text className="text-text-secondary text-xs mb-1">Barcode Value</Text>
        <View className="flex-row gap-2 mb-3">
          <TextInput
            className="flex-1 bg-secondary text-white rounded-lg px-3 py-2 text-sm"
            value={barcodeValue}
            onChangeText={setBarcodeValue}
            placeholder="Enter barcode..."
            placeholderTextColor="#7A9B88"
            autoCapitalize="none"
          />
          <TouchableOpacity
            className={`px-3 rounded-lg items-center justify-center ${
              scannerOpen ? "bg-error" : "bg-forest-green-light"
            }`}
            onPress={() => {
              if (!hasPermission) {
                requestPermission();
                return;
              }
              setScannerOpen((prev) => !prev);
            }}
            activeOpacity={0.7}
          >
            <Ionicons
              name={scannerOpen ? "close" : "scan-outline"}
              size={20}
              color="#D4E8DA"
            />
          </TouchableOpacity>
        </View>

        {/* Inline Camera Scanner */}
        {scannerOpen && (
          <View className="mb-3 rounded-xl overflow-hidden" style={{ height: 220 }}>
            {!hasPermission ? (
              <View className="flex-1 bg-secondary items-center justify-center">
                <Text className="text-text-muted text-xs mb-2">
                  Camera permission required
                </Text>
                <TouchableOpacity
                  className="bg-forest-green-light px-4 py-2 rounded-lg"
                  onPress={requestPermission}
                >
                  <Text className="text-text-secondary text-xs font-semibold">
                    Grant Permission
                  </Text>
                </TouchableOpacity>
              </View>
            ) : !device ? (
              <View className="flex-1 bg-secondary items-center justify-center">
                <Text className="text-text-muted text-xs">No camera found</Text>
              </View>
            ) : (
              <View style={{ flex: 1 }}>
                <Camera
                  style={StyleSheet.absoluteFill}
                  device={device}
                  isActive={scannerOpen}
                  codeScanner={codeScanner}
                />
                {/* Scanning overlay with corners */}
                <View style={scanStyles.overlay}>
                  <View style={scanStyles.frame}>
                    <View style={[scanStyles.corner, scanStyles.topLeft]} />
                    <View style={[scanStyles.corner, scanStyles.topRight]} />
                    <View style={[scanStyles.corner, scanStyles.bottomLeft]} />
                    <View style={[scanStyles.corner, scanStyles.bottomRight]} />
                  </View>
                </View>
                <Text className="absolute bottom-2 self-center text-white text-xs"
                  style={{ textShadowColor: "rgba(0,0,0,0.8)", textShadowRadius: 3 }}
                >
                  Point at barcode
                </Text>
              </View>
            )}
          </View>
        )}

        {/* Action Buttons */}
        <View className="flex-row gap-2 mb-4">
          <TouchableOpacity
            className="flex-1 bg-forest-green-light rounded-lg py-2.5 items-center"
            onPress={handleGenerate}
            activeOpacity={0.7}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator size="small" color="#D4E8DA" />
            ) : (
              <Text className="text-text-secondary font-semibold text-sm">
                Generate
              </Text>
            )}
          </TouchableOpacity>
          <TouchableOpacity
            className="flex-1 bg-secondary rounded-lg py-2.5 items-center"
            onPress={handleSupply}
            activeOpacity={0.7}
          >
            <Text className="text-text-muted text-sm">Supply</Text>
          </TouchableOpacity>
          <TouchableOpacity
            className="flex-1 bg-secondary rounded-lg py-2.5 items-center"
            onPress={handleCollection}
            activeOpacity={0.7}
          >
            <Text className="text-text-muted text-sm">Collection</Text>
          </TouchableOpacity>
        </View>

        {/* Error */}
        {error && (
          <View className="bg-red-900/30 rounded-lg p-3 mb-3">
            <Text className="text-error text-xs">{error}</Text>
          </View>
        )}

        {/* Creature Result */}
        {creature && (
          <View className="bg-secondary rounded-xl p-4 mb-4">
            {/* Header */}
            <View className="flex-row items-center justify-between mb-2">
              <Text className="text-white text-base font-bold">
                {creature.presentation.name}
              </Text>
              <View
                className="px-2 py-0.5 rounded-full"
                style={{ backgroundColor: rarityColor + "30" }}
              >
                <Text style={{ color: rarityColor, fontSize: 11, fontWeight: "700" }}>
                  {creature.classification.rarity}
                </Text>
              </View>
            </View>

            {/* Title */}
            <Text className="text-text-muted text-xs italic mb-3">
              {creature.presentation.title}
            </Text>

            {/* Status badges */}
            <View className="flex-row gap-2 mb-3">
              {result?.is_new_discovery && (
                <View className="bg-forest-green-light/30 px-2 py-0.5 rounded-full">
                  <Text className="text-accent-green text-xs">New Discovery</Text>
                </View>
              )}
              {result?.is_claimed_variant && (
                <View className="bg-amber-900/30 px-2 py-0.5 rounded-full">
                  <Text className="text-amber-400 text-xs">Claimed Variant</Text>
                </View>
              )}
              {result?.is_owner && (
                <View className="bg-blue-900/30 px-2 py-0.5 rounded-full">
                  <Text className="text-blue-400 text-xs">Owned</Text>
                </View>
              )}
            </View>

            {/* Classification */}
            <View className="mb-3">
              <Text className="text-text-secondary text-xs font-semibold mb-1">
                Classification
              </Text>
              <InfoRow label="Biome" value={creature.classification.biome} />
              <InfoRow label="Family" value={creature.classification.family} />
              <InfoRow label="Species" value={creature.classification.species} />
              <InfoRow label="Subtype" value={creature.classification.sub_type} />
              <InfoRow label="Element" value={creature.classification.element} />
              <InfoRow label="Temperament" value={creature.classification.temperament} />
              <InfoRow label="Size" value={creature.classification.size} />
              <InfoRow label="Variant" value={creature.classification.variant} />
            </View>

            {/* Stats */}
            <View className="mb-3">
              <Text className="text-text-secondary text-xs font-semibold mb-1">
                Stats
              </Text>
              <View className="flex-row flex-wrap gap-x-4 gap-y-1">
                <StatPill label="POW" value={creature.attributes.power} />
                <StatPill label="DEF" value={creature.attributes.defense} />
                <StatPill label="AGI" value={creature.attributes.agility} />
                <StatPill label="WIS" value={creature.attributes.wisdom} />
                <StatPill label="FER" value={creature.attributes.ferocity} />
                <StatPill label="MAG" value={creature.attributes.magic} />
                <StatPill label="LCK" value={creature.attributes.luck} />
              </View>
            </View>

            {/* Presentation */}
            <View className="mb-2">
              <Text className="text-text-secondary text-xs font-semibold mb-1">
                Visual
              </Text>
              <InfoRow label="Colors" value={`${creature.presentation.primary_color} / ${creature.presentation.secondary_color}`} />
              <InfoRow label="Sigil" value={creature.presentation.sigil} />
              <InfoRow label="Frame" value={creature.presentation.frame_style} />
            </View>

            {/* ID */}
            <View className="mt-2 pt-2 border-t border-forest-green-dark">
              <Text className="text-text-muted text-xs font-mono">
                {creature.identity.creature_id}
              </Text>
            </View>
          </View>
        )}

        {/* Supply Status */}
        {supply && (
          <View className="bg-secondary rounded-xl p-4 mb-4">
            <Text className="text-white text-sm font-bold mb-2">
              Supply Status (Season {supply.season})
            </Text>
            {supply.tiers.map((tier) => (
              <View key={tier.rarity} className="flex-row justify-between py-1">
                <Text
                  style={{
                    color: RARITY_COLORS[tier.rarity] || "#9CA3AF",
                    fontSize: 12,
                    fontWeight: "600",
                  }}
                >
                  {tier.rarity}
                </Text>
                <Text className="text-text-muted text-xs">
                  {tier.current_count} / {tier.max_count ?? "∞"}
                  {tier.remaining != null && ` (${tier.remaining} left)`}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Collection */}
        {collection && (
          <View className="bg-secondary rounded-xl p-4 mb-4">
            <Text className="text-white text-sm font-bold mb-2">
              My Collection ({collection.total} creatures)
            </Text>
            {collection.items.length === 0 ? (
              <Text className="text-text-muted text-xs">No creatures yet</Text>
            ) : (
              collection.items.map((item, i) => (
                <View key={i} className="flex-row justify-between py-1">
                  <Text className="text-text-secondary text-xs flex-1" numberOfLines={1}>
                    {item.creature?.presentation?.name || item.creature_id}
                  </Text>
                  <Text
                    style={{
                      color:
                        RARITY_COLORS[
                          item.creature?.classification?.rarity || ""
                        ] || "#9CA3AF",
                      fontSize: 11,
                    }}
                  >
                    {item.creature?.classification?.rarity || "?"}
                  </Text>
                </View>
              ))
            )}
          </View>
        )}

        <View className="h-8" />
      </ScrollView>
    </SafeAreaView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row justify-between py-0.5">
      <Text className="text-text-muted text-xs">{label}</Text>
      <Text className="text-text-secondary text-xs">
        {value.replace(/_/g, " ")}
      </Text>
    </View>
  );
}

function StatPill({ label, value }: { label: string; value: number }) {
  return (
    <View className="flex-row items-center gap-1">
      <Text className="text-text-muted text-xs">{label}</Text>
      <Text className="text-accent-green text-xs font-bold">{value}</Text>
    </View>
  );
}

const CORNER_SIZE = 20;
const CORNER_WIDTH = 3;

const scanStyles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
  },
  frame: {
    width: 160,
    height: 100,
  },
  corner: {
    position: "absolute",
    width: CORNER_SIZE,
    height: CORNER_SIZE,
  },
  topLeft: {
    top: 0,
    left: 0,
    borderTopWidth: CORNER_WIDTH,
    borderLeftWidth: CORNER_WIDTH,
    borderColor: "#8BB174",
  },
  topRight: {
    top: 0,
    right: 0,
    borderTopWidth: CORNER_WIDTH,
    borderRightWidth: CORNER_WIDTH,
    borderColor: "#8BB174",
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: CORNER_WIDTH,
    borderLeftWidth: CORNER_WIDTH,
    borderColor: "#8BB174",
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: CORNER_WIDTH,
    borderRightWidth: CORNER_WIDTH,
    borderColor: "#8BB174",
  },
});
