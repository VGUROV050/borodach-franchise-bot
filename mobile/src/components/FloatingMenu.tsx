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
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter, usePathname } from "expo-router";
import {
  Home,
  BarChart3,
  CheckSquare,
  Trophy,
  BookOpen,
  Bot,
  Phone,
  ClipboardList,
  User,
  X,
  Settings,
} from "lucide-react-native";
import { colors, spacing } from "@/lib/theme";

const MENU_ITEMS = [
  { Icon: Home, label: "Главная", route: "/" },
  { Icon: BarChart3, label: "Статистика", route: "/stats" },
  { Icon: CheckSquare, label: "Задачи", route: "/tasks" },
  { Icon: Trophy, label: "Рейтинг", route: "/rating" },
  { Icon: BookOpen, label: "Полезное", route: "/useful" },
  { Icon: Bot, label: "AI-ассистент", route: "/ai-chat" },
  { Icon: Phone, label: "Связь", route: "/contact" },
  { Icon: ClipboardList, label: "Опросы", route: "/polls" },
  { Icon: User, label: "Профиль", route: "/profile-screen" },
] as const;

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const GRID_GAP = 10;
const SIDE_PADDING = 24;
const ITEM_SIZE = (SCREEN_WIDTH - SIDE_PADDING * 2 - GRID_GAP * 2) / 3;
const ICON_SIZE = 28;
const GRID_RADIUS = 16;

export function FloatingMenu() {
  const [open, setOpen] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const router = useRouter();
  const pathname = usePathname();
  const insets = useSafeAreaInsets();

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

  function openSettings() {
    hide(() => router.push("/profile-screen" as never));
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
        <View style={styles.fabDots}>
          <View style={styles.fabDot} />
          <View style={styles.fabDot} />
          <View style={styles.fabDot} />
        </View>
      </TouchableOpacity>

      <Modal
        visible={open}
        transparent
        animationType="none"
        statusBarTranslucent
        onRequestClose={() => hide()}
      >
        <Animated.View style={[styles.fullOverlay, { opacity: fadeAnim }]}>
          <View style={[styles.safeArea, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
            <View style={styles.topBar}>
              <Text style={styles.menuTitle}>Меню</Text>
              <TouchableOpacity
                style={styles.settingsBtn}
                activeOpacity={0.7}
                onPress={openSettings}
                hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
              >
                <Settings size={20} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <View style={styles.gridCenter}>
              <View style={styles.grid}>
                {MENU_ITEMS.map((item) => {
                  const active = isActive(item.route);
                  const Icon = item.Icon;
                  return (
                    <TouchableOpacity
                      key={item.route}
                      style={[
                        styles.gridItem,
                        active ? styles.gridItemActive : styles.gridItemInactive,
                      ]}
                      activeOpacity={0.7}
                      onPress={() => navigate(item.route)}
                    >
                      <Icon size={ICON_SIZE} color={colors.accent} />
                      <View style={styles.gridItemSpacer} />
                      <Text
                        style={styles.gridLabel}
                        numberOfLines={2}
                      >
                        {item.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>

            <View style={styles.bottomCloseWrap}>
              <TouchableOpacity
                style={styles.closeFab}
                activeOpacity={0.85}
                onPress={() => hide()}
                hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}
              >
                <X size={24} color={colors.white} strokeWidth={2.5} />
              </TouchableOpacity>
            </View>
          </View>
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
  fabDots: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 5,
  },
  fabDot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: colors.white,
  },
  fullOverlay: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  safeArea: {
    flex: 1,
    backgroundColor: colors.bg,
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
    fontWeight: "600",
    color: colors.text,
  },
  settingsBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.cardAlt,
    alignItems: "center",
    justifyContent: "center",
  },
  gridCenter: {
    flex: 1,
    justifyContent: "flex-start",
    paddingHorizontal: SIDE_PADDING,
    paddingTop: spacing.sm,
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
    borderRadius: GRID_RADIUS,
    padding: 12,
    overflow: "hidden",
  },
  gridItemInactive: {
    backgroundColor: colors.cardAlt,
  },
  gridItemActive: {
    backgroundColor: colors.accentLight,
    borderWidth: 1,
    borderColor: colors.accent,
  },
  gridItemSpacer: {
    flex: 1,
    minHeight: 4,
  },
  gridLabel: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.text,
    textAlign: "left",
    alignSelf: "stretch",
  },
  bottomCloseWrap: {
    alignItems: "center",
    paddingBottom: spacing.lg,
    paddingTop: spacing.sm,
  },
  closeFab: {
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
  },
});
