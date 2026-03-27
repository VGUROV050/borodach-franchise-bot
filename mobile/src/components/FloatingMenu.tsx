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
import { SafeAreaView } from "react-native-safe-area-context";
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
const GRID_GAP = 10;
const SIDE_PADDING = 24;
const ITEM_SIZE = (SCREEN_WIDTH - SIDE_PADDING * 2 - GRID_GAP * 2) / 3;

export function FloatingMenu() {
  const [open, setOpen] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const router = useRouter();
  const pathname = usePathname();

  function show() {
    setOpen(true);
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 200,
      useNativeDriver: true,
    }).start();
  }

  function hide(cb?: () => void) {
    Animated.timing(fadeAnim, {
      toValue: 0,
      duration: 180,
      useNativeDriver: true,
    }).start(() => {
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
        <Animated.View style={[styles.fullOverlay, { opacity: fadeAnim }]}>
          <SafeAreaView style={styles.safeArea}>
            <View style={styles.topBar}>
              <Text style={styles.menuTitle}>Меню</Text>
              <TouchableOpacity
                style={styles.closeBtn}
                activeOpacity={0.7}
                onPress={() => hide()}
                hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
              >
                <Text style={styles.closeIcon}>✕</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.gridCenter}>
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
            </View>
          </SafeAreaView>
        </Animated.View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: "absolute",
    bottom: 40,
    alignSelf: "center",
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.accent,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 8,
    zIndex: 999,
  },
  fabIcon: {
    fontSize: 24,
    color: colors.white,
  },
  fullOverlay: {
    flex: 1,
    backgroundColor: colors.white,
  },
  safeArea: {
    flex: 1,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: SIDE_PADDING,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  menuTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.text,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.cardAlt,
    alignItems: "center",
    justifyContent: "center",
  },
  closeIcon: {
    fontSize: 16,
    color: colors.textSecondary,
    fontWeight: "600",
  },
  gridCenter: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: SIDE_PADDING,
    paddingBottom: 60,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: GRID_GAP,
    width: "100%",
  },
  gridItem: {
    width: ITEM_SIZE,
    aspectRatio: 1,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.md,
    backgroundColor: colors.cardAlt,
  },
  gridItemActive: {
    backgroundColor: colors.accentBg,
  },
  gridIcon: {
    fontSize: 30,
    marginBottom: 8,
  },
  gridLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.textSecondary,
    textAlign: "center",
  },
  gridLabelActive: {
    color: colors.accent,
    fontWeight: "700",
  },
});
