import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../context/AuthContext";
import * as characterService from "../../services/characters";
import CollectionCreatureCard from "../../components/CollectionCreatureCard";
import CreatureDetailModal from "../../components/CreatureDetailModal";
import type { CollectionResponse, CreatureCard } from "../../types";

export default function CollectionScreen() {
  const { apiReady } = useAuth();
  const [collection, setCollection] = useState<CollectionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCreature, setSelectedCreature] = useState<CreatureCard | null>(null);

  const fetchCollection = useCallback(
    async (isRefresh = false) => {
      if (!apiReady) return;
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);
      try {
        const data = await characterService.getMyCollection(0, 200);
        setCollection(data);
      } catch (err: any) {
        setError(err?.message || "Failed to load collection");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [apiReady]
  );

  useFocusEffect(
    useCallback(() => {
      fetchCollection();
    }, [fetchCollection])
  );

  // Aggregate duplicates: group by creature_id, keep first creature, count occurrences
  const aggregated: { creature: CreatureCard; count: number }[] = (() => {
    const items = collection?.items.filter((item) => item.creature) || [];
    const map = new Map<string, { creature: CreatureCard; count: number }>();
    for (const item of items) {
      const c = item.creature!;
      const id = c.identity.creature_id;
      const existing = map.get(id);
      if (existing) {
        existing.count++;
      } else {
        map.set(id, { creature: c, count: 1 });
      }
    }
    return Array.from(map.values());
  })();

  const renderItem = ({ item }: { item: { creature: CreatureCard; count: number } }) => (
    <CollectionCreatureCard
      creature={item.creature}
      count={item.count}
      onPress={() => setSelectedCreature(item.creature)}
    />
  );

  return (
    <SafeAreaView className="flex-1 bg-primary">
      {/* Header */}
      <View className="flex-row justify-between items-center px-6 py-4">
        <View>
          <Text className="text-bark-dark text-2xl font-bold">
            My Collection
          </Text>
          <Text className="text-text-muted text-sm">
            {collection?.total || 0} creature
            {(collection?.total || 0) !== 1 ? "s" : ""}
          </Text>
        </View>
      </View>

      {/* Content */}
      {loading && !refreshing ? (
        <View className="flex-1 justify-center items-center">
          <ActivityIndicator size="large" color="#7B8F6B" />
        </View>
      ) : error ? (
        <View className="flex-1 justify-center items-center px-8">
          <Ionicons name="alert-circle-outline" size={48} color="#C45A4A" />
          <Text className="text-error text-sm mt-4 text-center">{error}</Text>
        </View>
      ) : aggregated.length === 0 ? (
        <View className="flex-1 justify-center items-center px-8">
          <Ionicons name="albums-outline" size={64} color="#9A8D82" />
          <Text className="text-bark-dark text-lg font-bold mt-4">
            No Creatures Yet
          </Text>
          <Text className="text-text-muted text-sm text-center mt-2">
            Visit the Creator tab to scan barcodes and discover your first
            creature!
          </Text>
        </View>
      ) : (
        <FlatList
          data={aggregated}
          renderItem={renderItem}
          keyExtractor={(item) => item.creature.identity.creature_id}
          numColumns={2}
          contentContainerStyle={{ paddingHorizontal: 24, paddingBottom: 20 }}
          columnWrapperStyle={{ gap: 12, marginBottom: 12 }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => fetchCollection(true)}
              tintColor="#7B8F6B"
              colors={["#7B8F6B"]}
            />
          }
        />
      )}
      {/* Detail Modal */}
      <CreatureDetailModal
        creature={selectedCreature}
        visible={!!selectedCreature}
        onClose={() => setSelectedCreature(null)}
      />
    </SafeAreaView>
  );
}
