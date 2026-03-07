import React, { useState, useCallback } from "react";
import { View, Text, TouchableOpacity, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import ScanResultDisplay from "../../../components/ScanResultDisplay";
import FlipCard from "../../../components/FlipCard";
import { ShimmerRarity } from "../../../components/CardShimmer";

const SCAN_RESULT_KEY = "WILDERNESS_LAST_SCAN";

const RARITY_ORDER: ShimmerRarity[] = [
  "common",
  "uncommon",
  "rare",
  "epic",
  "legendary",
];

const RARITY_COLORS: Record<ShimmerRarity, string> = {
  common: "#9E9E9E",
  uncommon: "#C0C0C0",
  rare: "#FFD700",
  epic: "#9C27B0",
  legendary: "#FF6F00",
};

export default function ScanTestScreen() {
  const router = useRouter();
  const [scanResults, setScanResults] = useState<string[]>([]);
  const [isCardFlipped, setIsCardFlipped] = useState(false);
  const [latestScan, setLatestScan] = useState<string | null>(null);
  const [rarityIndex, setRarityIndex] = useState(2); // Start at "rare"

  const currentRarity = RARITY_ORDER[rarityIndex];

  useFocusEffect(
    useCallback(() => {
      const checkScanResult = async () => {
        const result = await AsyncStorage.getItem(SCAN_RESULT_KEY);
        if (result) {
          setScanResults((prev) => [result, ...prev]);
          setLatestScan(result);
          setIsCardFlipped(true);
          await AsyncStorage.removeItem(SCAN_RESULT_KEY);
        }
      };
      checkScanResult();
    }, [])
  );

  const handleScanPress = () => {
    router.push("/scanner");
  };

  const handleClearResults = () => {
    setScanResults([]);
    setLatestScan(null);
    setIsCardFlipped(false);
  };

  const handleCardTap = () => {
    setIsCardFlipped((prev) => !prev);
  };

  const cycleRarity = () => {
    setRarityIndex((prev) => (prev + 1) % RARITY_ORDER.length);
  };

  return (
    <SafeAreaView className="flex-1 bg-primary" edges={["bottom"]}>
      <ScrollView className="flex-1 px-6">
        {/* Scan Button */}
        <TouchableOpacity
          className="bg-forest-light rounded-2xl py-6 items-center mt-4 flex-row justify-center"
          onPress={handleScanPress}
          activeOpacity={0.8}
        >
          <Ionicons name="scan-outline" size={32} color="#fff" />
          <Text className="text-white text-lg font-semibold ml-3">
            Scan Barcode / QR Code
          </Text>
        </TouchableOpacity>

        {/* Flip Card */}
        <TouchableOpacity
          activeOpacity={0.9}
          onPress={handleCardTap}
          className="items-center mt-6"
        >
          <FlipCard
            isFlipped={isCardFlipped}
            backImage={require("../../../assets/images/card_designs/card-back.png")}
            frontImage={require("../../../assets/images/card_designs/card-front-common.png")}
            scannedText={latestScan ?? undefined}
            rarity={currentRarity}
          />
        </TouchableOpacity>
        <Text className="text-text-muted text-xs text-center mt-2">
          Tap card to flip
        </Text>

        {/* Rarity Tester */}
        <TouchableOpacity
          onPress={cycleRarity}
          className="mt-4 py-3 rounded-lg items-center border"
          style={{ borderColor: RARITY_COLORS[currentRarity] }}
          activeOpacity={0.7}
        >
          <Text
            style={{ color: RARITY_COLORS[currentRarity] }}
            className="font-semibold text-sm uppercase tracking-wider"
          >
            {currentRarity}
          </Text>
          <Text className="text-text-muted text-xs mt-1">
            Tap to cycle rarity
          </Text>
        </TouchableOpacity>

        {/* Scan Results */}
        <ScanResultDisplay
          results={scanResults}
          onClear={scanResults.length > 0 ? handleClearResults : undefined}
        />
      </ScrollView>
    </SafeAreaView>
  );
}
