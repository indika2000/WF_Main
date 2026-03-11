import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ImageBackground,
  Image,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useAuth } from "../../context/AuthContext";

export default function HomeScreen() {
  const { user } = useAuth();
  const router = useRouter();

  return (
    <ImageBackground
      source={require("../../assets/images/home_screen_bg.png")}
      style={{ flex: 1 }}
      resizeMode="cover"
    >
      <SafeAreaView className="flex-1">
        {/* Header */}
        <View className="flex-row justify-between items-center px-6 py-4">
          <View>
            <Text className="text-bark-dark text-2xl font-bold">
              WildernessFriends
            </Text>
            <Text className="text-text-muted text-sm">{user?.email}</Text>
          </View>
          <TouchableOpacity
            onPress={() => router.push("/(tabs)/profile")}
            className="p-2"
          >
            <Image
              source={require("../../assets/images/icons/profile.png")}
              style={{ width: 32, height: 32 }}
              resizeMode="contain"
            />
          </TouchableOpacity>
        </View>

        {/* Placeholder for future game content */}
        <View className="flex-1 justify-center items-center px-8">
          <Text className="text-text-muted text-base text-center">
            Your adventure begins here
          </Text>
        </View>
      </SafeAreaView>
    </ImageBackground>
  );
}
