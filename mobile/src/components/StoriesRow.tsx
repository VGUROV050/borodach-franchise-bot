import React from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Image,
} from "react-native";
import { colors, spacing } from "@/lib/theme";

export interface StoryItem {
  id: number;
  title: string;
  image_url: string | null;
  emoji: string;
  is_new: boolean;
}

const MOCK_STORIES: StoryItem[] = [
  { id: 1, title: "Акции", emoji: "🎁", image_url: null, is_new: true },
  { id: 2, title: "Новости", emoji: "📰", image_url: null, is_new: true },
  { id: 3, title: "Обучение", emoji: "🎓", image_url: null, is_new: false },
  { id: 4, title: "Продукция", emoji: "✂️", image_url: null, is_new: false },
  { id: 5, title: "Франшиза", emoji: "🏢", image_url: null, is_new: false },
];

interface Props {
  stories?: StoryItem[];
  onPress?: (story: StoryItem) => void;
}

export function StoriesRow({ stories = MOCK_STORIES, onPress }: Props) {
  if (stories.length === 0) return null;

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.container}
    >
      {stories.map((story) => (
        <TouchableOpacity
          key={story.id}
          style={styles.item}
          activeOpacity={0.7}
          onPress={() => onPress?.(story)}
        >
          <View style={[styles.ring, story.is_new && styles.ringNew]}>
            <View style={styles.circle}>
              {story.image_url ? (
                <Image
                  source={{ uri: story.image_url }}
                  style={styles.image}
                />
              ) : (
                <Text style={styles.emoji}>{story.emoji}</Text>
              )}
            </View>
          </View>
          <Text style={styles.label} numberOfLines={1}>
            {story.title}
          </Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const CIRCLE_SIZE = 64;
const RING_SIZE = CIRCLE_SIZE + 6;

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: spacing.md,
    gap: 14,
  },
  item: {
    alignItems: "center",
    width: RING_SIZE + 4,
  },
  ring: {
    width: RING_SIZE,
    height: RING_SIZE,
    borderRadius: RING_SIZE / 2,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  ringNew: {
    borderColor: colors.accent,
  },
  circle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    backgroundColor: colors.cardAlt,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  image: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
  },
  emoji: {
    fontSize: 28,
  },
  label: {
    fontSize: 11,
    fontWeight: "500",
    color: colors.textSecondary,
    marginTop: 6,
    textAlign: "center",
  },
});
