import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarStyle: {
          backgroundColor: "#0F1A14",
          borderTopColor: "#1A2E22",
        },
        tabBarActiveTintColor: "#8BB174",
        tabBarInactiveTintColor: "#7A9B88",
        headerShown: false,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color }) => (
            <Ionicons name="home-outline" size={28} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="dev-tools"
        options={{
          title: "Dev Tools",
          href: __DEV__ ? "/dev-tools" : null,
          tabBarIcon: ({ color }) => (
            <Ionicons name="construct-outline" size={28} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
