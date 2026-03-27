import React from "react";
import { ScrollView, Text, TouchableOpacity, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { colors, spacing, fonts, radius } from "@/lib/theme";

const MENU_ITEMS = [
  { icon: "📚", label: "Полезное", route: "/useful" },
  { icon: "🤖", label: "AI-ассистент", route: "/ai-chat" },
  { icon: "📞", label: "Связь с офисом", route: "/contact" },
  { icon: "📊", label: "Опросы", route: "/polls" },
  { icon: "👤", label: "Профиль", route: "/profile-screen" },
] as const;

export default function MoreScreen() {
  const router = useRouter();

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      {MENU_ITEMS.map((item) => (
        <TouchableOpacity
          key={item.route}
          style={styles.card}
          activeOpacity={0.7}
          onPress={() => router.push(item.route as never)}
        >
          <Text style={styles.icon}>{item.icon}</Text>
          <Text style={styles.label}>{item.label}</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    padding: spacing.md,
    gap: spacing.sm,
  },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.md,
  },
  icon: {
    fontSize: 24,
  },
  label: {
    ...fonts.medium,
    fontWeight: "600",
    flex: 1,
  },
  chevron: {
    fontSize: 22,
    color: colors.textMuted,
    fontWeight: "300",
  },
});
