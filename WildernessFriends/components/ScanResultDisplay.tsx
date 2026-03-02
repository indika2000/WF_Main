import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface ScanResultDisplayProps {
  results: string[];
  onClear?: () => void;
}

export default function ScanResultDisplay({
  results,
  onClear,
}: ScanResultDisplayProps) {
  if (results.length === 0) {
    return (
      <View className="mt-8 items-center">
        <Ionicons name="scan-outline" size={48} color="#7A9B88" />
        <Text className="text-text-muted mt-4 text-center">
          No scans yet. Tap the button above to scan a barcode or QR code.
        </Text>
      </View>
    );
  }

  return (
    <View className="mt-6">
      <View className="flex-row justify-between items-center mb-3">
        <Text className="text-white text-lg font-semibold">Scan Results</Text>
        {onClear && (
          <TouchableOpacity onPress={onClear}>
            <Text className="text-error text-sm">Clear All</Text>
          </TouchableOpacity>
        )}
      </View>
      {results.map((result, index) => (
        <View
          key={index}
          className="bg-secondary rounded-lg p-4 mb-2 border border-forest"
        >
          <Text className="text-white text-sm" selectable>
            {result}
          </Text>
        </View>
      ))}
    </View>
  );
}
