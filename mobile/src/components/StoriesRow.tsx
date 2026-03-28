import React from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from "react-native";
import { Tag, Newspaper, GraduationCap, Package, Store } from "lucide-react-native";
import { colors, spacing } from "@/lib/theme";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const FIT_COUNT = 5;
const SIDE_PAD = spacing.md;
const ITEM_WIDTH = (SCREEN_WIDTH - SIDE_PAD * 2) / FIT_COUNT;

export interface StoryItem {
  id: number;
  title: string;
  icon: string;
  is_new: boolean;
}

const ICON_MAP: Record<string, React.ComponentType<any>> = {
  tag: Tag,
  news: Newspaper,
  education: GraduationCap,
  package: Package,
  store: Store,
};

const MOCK_STORIES: StoryItem[] = [
  { id: 1, title: "Акции", icon: "tag", is_new: true },
  { id: 2, title: "Новости", icon: "news", is_new: true },
  { id: 3, title: "Обучение", icon: "education", is_new: false },
  { id: 4, title: "Продукция", icon: "package", is_new: false },
  { id: 5, title: "Франшиза", icon: "store", is_new: true },
];

interface Props {
  stories?: StoryItem[];
  onPress?: (story: StoryItem) => void;
}

function StoryCircle({
  story,
  onPress,
}: {
  story: StoryItem;
  onPress?: (s: StoryItem) => void;
}) {
  const IconComponent = ICON_MAP[story.icon] || Tag;
  return (
    <TouchableOpacity
      style={[styles.item, { width: ITEM_WIDTH }]}
      activeOpacity={0.7}
      onPress={() => onPress?.(story)}
    >
      <View
        style={[styles.ring, story.is_new ? styles.ringNew : styles.ringViewed]}
      >
        <View style={styles.circle}>
          <IconComponent size={24} color={colors.textSecondary} />
        </View>
      </View>
      <Text style={styles.label} numberOfLines={1}>
        {story.title}
      </Text>
    </TouchableOpacity>
  );
}

export function StoriesRow({ stories = MOCK_STORIES, onPress }: Props) {
  if (stories.length === 0) return null;

  if (stories.length <= FIT_COUNT) {
    return (
      <View style={styles.fitRow}>
        {stories.map((story) => (
          <StoryCircle key={story.id} story={story} onPress={onPress} />
        ))}
      </View>
    );
  }

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.scrollContainer}
    >
      {stories.map((story) => (
        <StoryCircle key={story.id} story={story} onPress={onPress} />
      ))}
    </ScrollView>
  );
}

const CIRCLE_SIZE = 50;
const RING_SIZE = 58;

const styles = StyleSheet.create({
  fitRow: {
    flexDirection: "row",
    paddingHorizontal: SIDE_PAD,
    paddingBottom: spacing.sm,
  },
  scrollContainer: {
    paddingHorizontal: SIDE_PAD,
    paddingBottom: spacing.sm,
  },
  item: {
    alignItems: "center",
  },
  ring: {
    width: RING_SIZE,
    height: RING_SIZE,
    borderRadius: RING_SIZE / 2,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg,
  },
  ringNew: {
    borderColor: colors.accent,
  },
  ringViewed: {
    borderColor: colors.textMuted,
  },
  circle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    backgroundColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  label: {
    fontSize: 11,
    fontWeight: "400",
    color: colors.textSecondary,
    marginTop: 6,
    textAlign: "center",
  },
});
