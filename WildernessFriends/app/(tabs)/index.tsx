import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../context/AuthContext";

export default function HomeScreen() {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <SafeAreaView className="flex-1 bg-primary">
      {/* Header */}
      <View className="flex-row justify-between items-center px-6 py-4">
        <View>
          <Text className="text-white text-2xl font-bold">
            WildernessFriends
          </Text>
          <Text className="text-text-muted text-sm">{user?.email}</Text>
        </View>
        <TouchableOpacity onPress={handleLogout} className="p-2">
          <Ionicons name="log-out-outline" size={24} color="#E53935" />
        </TouchableOpacity>
      </View>

      {/* Placeholder for future game content */}
      <View className="flex-1 justify-center items-center px-8">
        <Ionicons name="leaf-outline" size={64} color="#2D5A45" />
        <Text className="text-text-muted text-base mt-4 text-center">
          Your collection will appear here
        </Text>
      </View>
    </SafeAreaView>
  );
}
