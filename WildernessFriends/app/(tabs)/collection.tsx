import React from "react";
import { View, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

export default function CollectionScreen() {
  return (
    <SafeAreaView className="flex-1 bg-primary">
      <View className="flex-1 justify-center items-center px-8">
        <Text className="text-bark-dark text-xl font-bold mb-2">
          Collection
        </Text>
        <Text className="text-text-muted text-base text-center">
          Your collected creatures will appear here
        </Text>
      </View>
    </SafeAreaView>
  );
}
