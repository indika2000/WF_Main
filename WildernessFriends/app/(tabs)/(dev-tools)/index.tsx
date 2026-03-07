import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useAuth } from "../../../context/AuthContext";
import * as cartService from "../../../services/cart";
import * as commerce from "../../../services/commerce";
import * as permissionsService from "../../../services/permissions";
import * as devTools from "../../../services/devTools";
import type { Cart, Order, Subscription, UserPermissions } from "../../../types";

const WEBHOOK_EVENTS = [
  "payment_intent.succeeded",
  "payment_intent.payment_failed",
  "customer.subscription.created",
  "customer.subscription.updated",
  "customer.subscription.deleted",
  "invoice.payment_succeeded",
  "invoice.payment_failed",
];

type ResultData = Cart | Order[] | Subscription | UserPermissions | null;

export default function DevToolsLandingScreen() {
  const { user, apiReady, permissions } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<string>("");
  const [selectedEvent, setSelectedEvent] = useState(0);

  const userId = user?.uid ?? "";

  const runAction = async (label: string, action: () => Promise<unknown>) => {
    if (!apiReady) {
      Alert.alert("Not Ready", "API not connected. Wait for token exchange.");
      return;
    }
    setLoading(true);
    setLastResult(`Running: ${label}...`);
    try {
      const result = await action();
      setLastResult(
        `${label}\n\nResult:\n${JSON.stringify(result, null, 2)}`
      );
    } catch (err: any) {
      setLastResult(
        `${label}\n\nError:\n${JSON.stringify(err, null, 2)}`
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-primary">
      <ScrollView className="flex-1 px-4 py-2">
        {/* Header */}
        <Text className="text-white text-xl font-bold mb-1">Dev Tools</Text>
        <Text className="text-text-muted text-xs mb-4">
          {apiReady ? "API Connected" : "API Not Connected"} | {user?.email}
        </Text>

        {/* --- Navigation Cards --- */}
        <View className="flex-row flex-wrap gap-3 mb-4">
          <TouchableOpacity
            className="bg-secondary rounded-xl p-4 items-center"
            style={{ width: "47%" }}
            activeOpacity={0.7}
            onPress={() => router.push("/(dev-tools)/scan-test")}
          >
            <Ionicons name="scan-outline" size={28} color="#8BB174" />
            <Text className="text-text-secondary text-xs font-semibold mt-2 text-center">
              Scan & Card Test
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            className="bg-secondary rounded-xl p-4 items-center"
            style={{ width: "47%" }}
            activeOpacity={0.7}
            onPress={() => router.push("/(dev-tools)/card-layer-test")}
          >
            <Ionicons name="layers-outline" size={28} color="#8BB174" />
            <Text className="text-text-secondary text-xs font-semibold mt-2 text-center">
              Card Layer Test
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            className="bg-secondary rounded-xl p-4 items-center"
            style={{ width: "47%" }}
            activeOpacity={0.7}
            onPress={() => router.push("/(dev-tools)/character-gen-test")}
          >
            <Ionicons name="paw-outline" size={28} color="#8BB174" />
            <Text className="text-text-secondary text-xs font-semibold mt-2 text-center">
              Character Generator
            </Text>
          </TouchableOpacity>
        </View>

        {/* --- Cart Tester --- */}
        <SectionHeader title="Cart" icon="cart-outline" />
        <ButtonRow>
          <ActionButton
            label="Add Test Item"
            onPress={() =>
              runAction("Add Item to Cart", () =>
                cartService.addItem(userId, {
                  item_id: "pack-001",
                  item_type: "pack",
                  name: "Starter Pack",
                  quantity: 1,
                  unit_price: 4.99,
                })
              )
            }
          />
          <ActionButton
            label="View Cart"
            onPress={() =>
              runAction("Get Cart", () => cartService.getCart(userId))
            }
          />
          <ActionButton
            label="Clear Cart"
            color="#E53935"
            onPress={() =>
              runAction("Clear Cart", () => cartService.clearCart(userId))
            }
          />
        </ButtonRow>

        {/* --- Payment Tester --- */}
        <SectionHeader title="Checkout" icon="card-outline" />
        <ButtonRow>
          <ActionButton
            label="Validate Cart"
            onPress={() =>
              runAction("Validate Cart", () =>
                commerce.validateCart(userId)
              )
            }
          />
          <ActionButton
            label="Create Payment"
            onPress={() =>
              runAction("Create Payment", () =>
                commerce.createPayment(userId)
              )
            }
          />
        </ButtonRow>

        {/* --- Subscription Tester --- */}
        <SectionHeader title="Subscriptions" icon="star-outline" />
        <ButtonRow>
          <ActionButton
            label="View Sub"
            onPress={() =>
              runAction("Get Subscription", () =>
                commerce.getSubscription(userId)
              )
            }
          />
          <ActionButton
            label="Create Premium"
            onPress={() =>
              runAction("Create Premium Sub", () =>
                commerce.createSubscription(userId, "premium")
              )
            }
          />
          <ActionButton
            label="Cancel Sub"
            color="#E53935"
            onPress={() =>
              runAction("Cancel Subscription", () =>
                commerce.cancelSubscription(userId)
              )
            }
          />
        </ButtonRow>

        {/* --- Webhook Simulator --- */}
        <SectionHeader title="Webhook Simulator" icon="flash-outline" />
        <View className="flex-row flex-wrap mb-2">
          {WEBHOOK_EVENTS.map((evt, idx) => (
            <TouchableOpacity
              key={evt}
              className="px-2 py-1 rounded mr-2 mb-2"
              style={{
                backgroundColor:
                  idx === selectedEvent ? "#8BB174" : "#1A2E22",
              }}
              onPress={() => setSelectedEvent(idx)}
            >
              <Text
                className="text-xs"
                style={{
                  color: idx === selectedEvent ? "#0F1A14" : "#7A9B88",
                }}
              >
                {evt.replace("customer.", "").replace("payment_intent.", "pi.")}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        <ActionButton
          label={`Fire: ${WEBHOOK_EVENTS[selectedEvent]}`}
          color="#FF9800"
          onPress={() =>
            runAction(
              `Simulate ${WEBHOOK_EVENTS[selectedEvent]}`,
              () =>
                devTools.simulateWebhook(
                  WEBHOOK_EVENTS[selectedEvent],
                  userId
                )
            )
          }
        />

        {/* --- State Viewer --- */}
        <SectionHeader title="State Viewer" icon="eye-outline" />
        <ButtonRow>
          <ActionButton
            label="Permissions"
            onPress={() =>
              runAction("Get Permissions", () =>
                permissionsService.getPermissions(userId)
              )
            }
          />
          <ActionButton
            label="Orders"
            onPress={() =>
              runAction("Get Orders", () =>
                commerce.getOrders(userId)
              )
            }
          />
          <ActionButton
            label="Profile"
            onPress={() =>
              runAction("Get Profile", () =>
                commerce.getProfile(userId)
              )
            }
          />
        </ButtonRow>

        {/* --- Current Permissions (from context) --- */}
        <SectionHeader title="Context State" icon="information-circle-outline" />
        <View className="bg-secondary rounded-lg p-3 mb-4">
          <Text className="text-text-muted text-xs font-mono">
            {JSON.stringify(
              {
                apiReady,
                role: permissions?.role,
                is_premium: permissions?.is_premium,
                tier: permissions?.subscription?.tier,
              },
              null,
              2
            )}
          </Text>
        </View>

        {/* --- Result Display --- */}
        {(loading || lastResult) && (
          <View className="bg-secondary rounded-lg p-3 mb-8">
            {loading && (
              <ActivityIndicator color="#8BB174" className="mb-2" />
            )}
            <Text className="text-text-secondary text-xs font-mono">
              {lastResult}
            </Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

// --- Helper Components ---

function SectionHeader({
  title,
  icon,
}: {
  title: string;
  icon: keyof typeof Ionicons.glyphMap;
}) {
  return (
    <View className="flex-row items-center mt-4 mb-2">
      <Ionicons name={icon} size={18} color="#8BB174" />
      <Text className="text-text-accent text-sm font-semibold ml-2">
        {title}
      </Text>
    </View>
  );
}

function ButtonRow({ children }: { children: React.ReactNode }) {
  return <View className="flex-row flex-wrap gap-2 mb-2">{children}</View>;
}

function ActionButton({
  label,
  onPress,
  color,
}: {
  label: string;
  onPress: () => void;
  color?: string;
}) {
  return (
    <TouchableOpacity
      className="px-3 py-2 rounded-lg"
      style={{ backgroundColor: color || "#2D5A45" }}
      activeOpacity={0.7}
      onPress={onPress}
    >
      <Text className="text-white text-xs font-semibold">{label}</Text>
    </TouchableOpacity>
  );
}
