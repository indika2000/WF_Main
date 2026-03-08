import { Tabs } from "expo-router";
import { Image } from "react-native";
import { Ionicons } from "@expo/vector-icons";

function TabIcon({
  source,
  focused,
}: {
  source: any;
  focused: boolean;
}) {
  return (
    <Image
      source={source}
      style={{ width: 26, height: 26, opacity: focused ? 1 : 0.4 }}
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
          tabBarIcon: ({ focused }) => (
            <TabIcon
              source={require("../../assets/images/icons/home.png")}
              focused={focused}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="collection"
        options={{
          title: "Collection",
          tabBarIcon: ({ focused }) => (
            <TabIcon
              source={require("../../assets/images/icons/collection.png")}
              focused={focused}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="character-creator"
        options={{
          title: "Creator",
          tabBarIcon: ({ focused }) => (
            <TabIcon
              source={require("../../assets/images/icons/character_creator.png")}
              focused={focused}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="marketplace"
        options={{
          title: "Market",
          tabBarIcon: ({ focused }) => (
            <TabIcon
              source={require("../../assets/images/icons/marketplace.png")}
              focused={focused}
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
