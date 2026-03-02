import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Alert,
  StyleSheet,
  Image,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Video, ResizeMode } from "expo-av";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  interpolate,
  Easing,
} from "react-native-reanimated";
import { useAuth } from "../context/AuthContext";

function BannerWithShimmer() {
  const shimmer = useSharedValue(0);

  useEffect(() => {
    shimmer.value = withRepeat(
      withTiming(1, { duration: 4000, easing: Easing.inOut(Easing.ease) }),
      -1,
      true
    );
  }, []);

  const shimmerStyle = useAnimatedStyle(() => {
    const translateX = interpolate(shimmer.value, [0, 1], [-200, 200]);
    const opacity = interpolate(
      shimmer.value,
      [0, 0.3, 0.5, 0.7, 1],
      [0.03, 0.08, 0.12, 0.08, 0.03]
    );
    return {
      transform: [{ translateX }],
      opacity,
    };
  });

  return (
    <View
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 3,
        alignItems: "center",
        paddingTop: 50,
      }}
      pointerEvents="none"
    >
      {/* Wide glow behind the banner */}
      <View
        style={{
          position: "absolute",
          top: 55,
          left: "-5%",
          right: "-5%",
          height: 160,
          borderRadius: 80,
          backgroundColor: "rgba(139, 177, 116, 0.08)",
          shadowColor: "#8BB174",
          shadowOffset: { width: 0, height: 0 },
          shadowOpacity: 0.3,
          shadowRadius: 60,
          elevation: 20,
          overflow: "hidden",
        }}
      >
        {/* Subtle travelling shimmer */}
        <Animated.View
          style={[
            {
              position: "absolute",
              top: -20,
              width: 180,
              height: 200,
              borderRadius: 90,
              backgroundColor: "rgba(212, 232, 218, 0.15)",
            },
            shimmerStyle,
          ]}
        />
      </View>
      <Image
        source={require("../assets/images/Banner_Login_top.png")}
        style={{ width: "100%", height: 170 }}
        resizeMode="stretch"
      />
    </View>
  );
}

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const { login, register, loading, error, setError } = useAuth();

  React.useEffect(() => {
    setError(null);
  }, [isLogin]);

  const handleSubmit = async () => {
    if (!email || !password) {
      Alert.alert("Error", "Please fill in all fields");
      return;
    }
    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password);
      }
    } catch {
      // Error handled in AuthContext
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: "#ffffff" }}>
      {/* Full-screen background video */}
      <Video
        source={require("../assets/videos/login-bg.mp4")}
        style={StyleSheet.absoluteFill}
        resizeMode={ResizeMode.COVER}
        shouldPlay
        isLooping
        isMuted
      />

      {/* Dark overlay */}
      <View
        style={[
          StyleSheet.absoluteFill,
          { backgroundColor: "rgba(15, 26, 20, 0.7)", zIndex: 2 },
        ]}
      />

      {/* Banner with shimmer glow behind it */}
      <BannerWithShimmer />

      <SafeAreaView className="flex-1" style={{ zIndex: 4 }}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          className="flex-1"
        >
          {/* Spacer pushes form to bottom */}
          <View style={{ flex: 1 }} />

          {/* Form card */}
          <View
            style={{
              marginHorizontal: 20,
              marginBottom: 16,
              backgroundColor: "rgba(15, 26, 20, 0.75)",
              borderRadius: 20,
              borderWidth: 1,
              borderColor: "rgba(139, 177, 116, 0.15)",
              paddingHorizontal: 20,
              paddingTop: 24,
              paddingBottom: 20,
            }}
          >
            {/* Error display */}
            {error && (
              <View className="bg-red-500/20 p-3 rounded-lg mb-4">
                <Text className="text-red-400 text-center">{error}</Text>
              </View>
            )}

            {/* Email */}
            <View style={{ marginBottom: 16 }}>
              <Text style={{ color: "#D4E8DA", fontSize: 13, marginBottom: 6, marginLeft: 4 }}>Email</Text>
              <TextInput
                style={styles.input}
                placeholder="your@email.com"
                placeholderTextColor="#5A7B68"
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
                textContentType="emailAddress"
              />
            </View>

            {/* Password */}
            <View style={{ marginBottom: 24 }}>
              <Text style={{ color: "#D4E8DA", fontSize: 13, marginBottom: 6, marginLeft: 4 }}>Password</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter your password"
                placeholderTextColor="#5A7B68"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
                textContentType={isLogin ? "password" : "newPassword"}
              />
            </View>

            {/* Submit button */}
            <TouchableOpacity
              style={styles.submitButton}
              onPress={handleSubmit}
              disabled={loading}
              activeOpacity={0.8}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={{ color: "#fff", fontWeight: "700", fontSize: 16 }}>
                  {isLogin ? "Sign In" : "Create Account"}
                </Text>
              )}
            </TouchableOpacity>

            {/* Toggle */}
            <View className="flex-row justify-center mt-6">
              <Text className="text-text-muted">
                {isLogin
                  ? "Don't have an account? "
                  : "Already have an account? "}
              </Text>
              <TouchableOpacity onPress={() => setIsLogin(!isLogin)}>
                <Text className="text-text-accent font-semibold">
                  {isLogin ? "Create Account" : "Sign In"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Footer */}
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", paddingTop: 12, paddingBottom: 16 }}>
            <Image
              source={require("../assets/company_logo_name.png")}
              style={{ width: 40, height: 40, marginRight: 10 }}
              resizeMode="contain"
            />
            <View>
              <Text style={{ color: "#7A9B88", fontSize: 10 }}>
                {"\u00A9"} 2026 Caps and Capes. All rights reserved.
              </Text>
              <Text style={{ color: "#7A9B88", fontSize: 9, marginTop: 2 }}>
                WildernessFriends{"\u2122"} is a trademark of Caps and Capes.
              </Text>
            </View>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  input: {
    backgroundColor: "rgba(27, 58, 45, 0.6)",
    borderWidth: 1,
    borderColor: "rgba(139, 177, 116, 0.3)",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 15,
    color: "#fff",
  },
  submitButton: {
    backgroundColor: "#2D5A45",
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: "center",
    shadowColor: "#8BB174",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 8,
  },
});
