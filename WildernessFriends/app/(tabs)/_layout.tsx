import { Tabs } from "expo-router";
import { Image } from "react-native";
import { Ionicons } from "@expo/vector-icons";

function TabIcon({ source, color }: { source: any; color: string }) {
  return (
    <Image
      source={source}
      style={{ width: 26, height: 26, tintColor: color }}
      resizeMode="contain"
    />
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarStyle: {
          backgroundColor: "#F5F0E8",
          borderTopColor: "#E8E0D4",
        },
        tabBarActiveTintColor: "#5A6B4A",
        tabBarInactiveTintColor: "#9A8D82",
        headerShown: false,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color }) => (
            <TabIcon
              source={require("../../assets/images/icons/home.png")}
              color={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="collection"
        options={{
          title: "Collection",
          tabBarIcon: ({ color }) => (
            <TabIcon
              source={require("../../assets/images/icons/collection.png")}
              color={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="character-creator"
        options={{
          title: "Creator",
          tabBarIcon: ({ color }) => (
            <TabIcon
              source={require("../../assets/images/icons/character_creator.png")}
              color={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="marketplace"
        options={{
          title: "Market",
          tabBarIcon: ({ color }) => (
            <TabIcon
              source={require("../../assets/images/icons/marketplace.png")}
              color={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="(dev-tools)"
        options={{
          title: "Dev Tools",
          headerShown: false,
          href: __DEV__ ? "/(dev-tools)" : null,
          tabBarIcon: ({ color }) => (
            <Ionicons name="construct-outline" size={28} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
