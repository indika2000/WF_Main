import { Stack } from "expo-router";

export default function DevToolsLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: "#0F1A14" },
        headerTintColor: "#8BB174",
        headerTitleStyle: { color: "#D4E8DA", fontWeight: "600" },
        contentStyle: { backgroundColor: "#0F1A14" },
      }}
    >
      <Stack.Screen
        name="index"
        options={{ title: "Dev Tools", headerShown: false }}
      />
      <Stack.Screen
        name="scan-test"
        options={{ title: "Scan & Card Test" }}
      />
      <Stack.Screen
        name="card-layer-test"
        options={{ title: "Card Layer Test" }}
      />
      <Stack.Screen
        name="character-gen-test"
        options={{ title: "Character Generator" }}
      />
    </Stack>
  );
}
