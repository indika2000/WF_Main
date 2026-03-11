import React from "react";
import { View, Text, TouchableOpacity, Image, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../context/AuthContext";

export default function ProfileScreen() {
  const { user, logout } = useAuth();

  return (
    <SafeAreaView className="flex-1 bg-primary">
      <View className="flex-1 px-6 py-4">
        {/* Header */}
        <Text className="text-bark-dark text-2xl font-bold mb-6">Profile</Text>

        {/* Avatar + Email */}
        <View className="items-center mb-8">
          <View style={styles.avatarContainer}>
            <Image
              source={require("../../assets/images/icons/profile.png")}
              style={styles.avatar}
              resizeMode="contain"
            />
          </View>
          <Text className="text-bark-dark text-lg font-semibold mt-4">
            {user?.email || "Adventurer"}
          </Text>
          <Text className="text-text-muted text-sm mt-1">
            Free Tier
          </Text>
        </View>

        {/* Placeholder sections */}
        <View className="bg-secondary rounded-xl p-4 mb-4">
          <View className="flex-row items-center mb-3">
            <Ionicons name="settings-outline" size={20} color="#6B5B4F" />
            <Text className="text-text-secondary text-base font-semibold ml-3">
              Settings
            </Text>
          </View>
          <Text className="text-text-muted text-sm">
            Account settings coming soon
          </Text>
        </View>

        <View className="bg-secondary rounded-xl p-4 mb-4">
          <View className="flex-row items-center mb-3">
            <Ionicons name="diamond-outline" size={20} color="#6B5B4F" />
            <Text className="text-text-secondary text-base font-semibold ml-3">
              Subscription
            </Text>
          </View>
          <Text className="text-text-muted text-sm">
            Upgrade options coming soon
          </Text>
        </View>

        {/* Spacer */}
        <View className="flex-1" />

        {/* Logout */}
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={logout}
          activeOpacity={0.8}
        >
          <Ionicons name="log-out-outline" size={20} color="#C45A4A" />
          <Text style={styles.logoutText}>Log Out</Text>
        </TouchableOpacity>

        <View className="h-4" />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  avatarContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#F5F0E8",
    borderWidth: 2,
    borderColor: "#E8E0D4",
    justifyContent: "center",
    alignItems: "center",
    overflow: "hidden",
  },
  avatar: {
    width: 50,
    height: 50,
  },
  logoutButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "#C45A4A",
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
  },
  logoutText: {
    color: "#C45A4A",
    fontSize: 16,
    fontWeight: "600",
  },
});
