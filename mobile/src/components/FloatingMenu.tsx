import React, { useState, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  Animated,
  StyleSheet,
  Dimensions,
} from "react-native";
import { useRouter, usePathname } from "expo-router";
import { colors, spacing, radius } from "@/lib/theme";

const MENU_ITEMS = [
  { icon: "🏠", label: "Главная", route: "/" },
  { icon: "📊", label: "Статистика", route: "/stats" },
  { icon: "📋", label: "Задачи", route: "/tasks" },
  { icon: "🏆", label: "Рейтинг", route: "/rating" },
  { icon: "📚", label: "Полезное", route: "/useful" },
  { icon: "🤖", label: "AI-ассистент", route: "/ai-chat" },
  { icon: "📞", label: "Связь", route: "/contact" },
  { icon: "📊", label: "Опросы", route: "/polls" },
  { icon: "👤", label: "Профиль", route: "/profile-screen" },
] as const;

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const GRID_PADDING = 24;
const GRID_GAP = 12;
const ITEM_SIZE = (SCREEN_WIDTH - GRID_PADDING * 2 - GRID_GAP * 2) / 3;

export function FloatingMenu() {
  const [open, setOpen] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.9)).current;
  const router = useRouter();
  const pathname = usePathname();

  function show() {
    setOpen(true);
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        tension: 100,
        useNativeDriver: true,
      }),
    ]).start();
  }

  function hide(cb?: () => void) {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 150,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 0.9,
        duration: 150,
        useNativeDriver: true,
      }),
    ]).start(() => {
      setOpen(false);
      cb?.();
    });
  }

  function navigate(route: string) {
    hide(() => router.push(route as never));
  }

  function isActive(route: string) {
    if (route === "/") return pathname === "/";
    return pathname.startsWith(route);
  }

  return (
    <>
      <TouchableOpacity
        style={styles.fab}
        activeOpacity={0.85}
        onPress={show}
      >
        <Text style={styles.fabIcon}>⊞</Text>
      </TouchableOpacity>

      <Modal
        visible={open}
        transparent
        animationType="none"
        statusBarTranslucent
        onRequestClose={() => hide()}
      >
        <Animated.View style={[styles.overlay, { opacity: fadeAnim }]}>
          <TouchableOpacity
            style={styles.overlayBg}
            activeOpacity={1}
            onPress={() => hide()}
          />

          <Animated.View
            style={[
              styles.menuCard,
              { opacity: fadeAnim, transform: [{ scale: scaleAnim }] },
            ]}
          >
            <View style={styles.grid}>
              {MENU_ITEMS.map((item) => (
                <TouchableOpacity
                  key={item.route}
                  style={[
                    styles.gridItem,
                    isActive(item.route) && styles.gridItemActive,
                  ]}
                  activeOpacity={0.7}
                  onPress={() => navigate(item.route)}
                >
                  <Text style={styles.gridIcon}>{item.icon}</Text>
                  <Text
                    style={[
                      styles.gridLabel,
                      isActive(item.route) && styles.gridLabelActive,
                    ]}
                    numberOfLines={1}
                  >
                    {item.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </Animated.View>

          <TouchableOpacity
            style={styles.closeBtn}
            activeOpacity={0.8}
            onPress={() => hide()}
          >
            <Text style={styles.closeIcon}>✕</Text>
          </TouchableOpacity>
        </Animated.View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: "absolute",
    bottom: 30,
    alignSelf: "center",
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.accent,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 8,
    elevation: 8,
    zIndex: 999,
  },
  fabIcon: {
    fontSize: 24,
    color: colors.white,
  },
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    alignItems: "center",
    paddingBottom: 100,
  },
  overlayBg: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.3)",
  },
  menuCard: {
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    paddingVertical: spacing.lg,
    paddingHorizontal: GRID_PADDING,
    marginHorizontal: spacing.md,
    width: SCREEN_WIDTH - spacing.md * 2,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 24,
    elevation: 12,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: GRID_GAP,
  },
  gridItem: {
    width: ITEM_SIZE,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.cardAlt,
  },
  gridItemActive: {
    backgroundColor: colors.accentBg,
  },
  gridIcon: {
    fontSize: 28,
    marginBottom: spacing.xs,
  },
  gridLabel: {
    fontSize: 11,
    fontWeight: "600",
    color: colors.textSecondary,
    textAlign: "center",
  },
  gridLabelActive: {
    color: colors.accent,
    fontWeight: "700",
  },
  closeBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
    marginTop: spacing.md,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  closeIcon: {
    fontSize: 18,
    color: colors.text,
    fontWeight: "600",
  },
});
