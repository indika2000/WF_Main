import React, { useState } from "react";
import { View, Text, TouchableOpacity, ScrollView, Dimensions } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import LayeredFlipCard from "../../../components/LayeredFlipCard";

const SCREEN_WIDTH = Dimensions.get("window").width;
const CARD_WIDTH = (SCREEN_WIDTH - 48) / 2; // 16px padding each side + 16px gap
const CARD_HEIGHT = CARD_WIDTH * 1.5; // Matches image aspect ratio (1024x1536 = 2:3)

const BASES = [
  {
    id: "normal",
    label: "Normal",
    image: require("../../../assets/images/card_designs/card_backing-normal.png"),
  },
  {
    id: "uncommon",
    label: "Uncommon",
    image: require("../../../assets/images/card_designs/card_backing_uncommon.png"),
  },
  {
    id: "rare",
    label: "Rare",
    image: require("../../../assets/images/card_designs/card_backing_rare.png"),
  },
];

const CHARACTER = require("../../../assets/images/card_designs/test_painted_character.png");

const BORDERS = [
  {
    id: "1",
    label: "Border 1",
    image: require("../../../assets/images/card_designs/border_1_transparent.png"),
  },
  {
    id: "2",
    label: "Border 2",
    image: require("../../../assets/images/card_designs/border_2_transparent.png"),
  },
  {
    id: "3",
    label: "Border 3",
    image: require("../../../assets/images/card_designs/border_3_transparent.png"),
  },
  {
    id: "4",
    label: "Border 4",
    image: require("../../../assets/images/card_designs/border_4_transparent.png"),
  },
];

const CARD_BACK = require("../../../assets/images/card_designs/card-back.png");

type CardCombo = {
  key: string;
  base: (typeof BASES)[0];
  border: (typeof BORDERS)[0];
};

const ALL_COMBOS: CardCombo[] = BASES.flatMap((base) =>
  BORDERS.map((border) => ({
    key: `${base.id}-${border.id}`,
    base,
    border,
  }))
);

export default function CardLayerTestScreen() {
  const [flippedCards, setFlippedCards] = useState<Record<string, boolean>>({});

  const toggleFlip = (key: string) => {
    setFlippedCards((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const flipAll = () => {
    const allFlipped = ALL_COMBOS.every((c) => flippedCards[c.key]);
    const newState: Record<string, boolean> = {};
    ALL_COMBOS.forEach((c) => {
      newState[c.key] = !allFlipped;
    });
    setFlippedCards(newState);
  };

  return (
    <SafeAreaView className="flex-1 bg-primary" edges={["bottom"]}>
      <ScrollView className="flex-1 px-4">
        <Text className="text-text-secondary text-xs text-center mt-2">
          {ALL_COMBOS.length} combinations — Tap any card to flip
        </Text>
        <TouchableOpacity
          onPress={flipAll}
          className="self-center mt-1 mb-4 px-4 py-1 rounded-full bg-secondary"
          activeOpacity={0.7}
        >
          <Text className="text-text-muted text-xs">Flip All</Text>
        </TouchableOpacity>

        <View
          style={{
            flexDirection: "row",
            flexWrap: "wrap",
            justifyContent: "space-between",
          }}
        >
          {ALL_COMBOS.map((combo) => (
            <View
              key={combo.key}
              style={{
                width: CARD_WIDTH,
                marginBottom: 24,
                alignItems: "center",
              }}
            >
              <TouchableOpacity
                activeOpacity={0.9}
                onPress={() => toggleFlip(combo.key)}
                style={{ width: CARD_WIDTH, height: CARD_HEIGHT }}
              >
                <LayeredFlipCard
                  isFlipped={!!flippedCards[combo.key]}
                  baseImage={combo.base.image}
                  characterImage={CHARACTER}
                  borderImage={combo.border.image}
                  backImage={CARD_BACK}
                  lightText={combo.base.id === "rare"}
                  width={CARD_WIDTH}
                  height={CARD_HEIGHT}
                />
              </TouchableOpacity>
              <Text className="text-text-muted text-xs mt-1 text-center">
                {combo.base.label} / {combo.border.label}
              </Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
