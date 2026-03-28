import React, { useState, useCallback, useRef } from "react";
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  RefreshControl,
  Dimensions,
  NativeSyntheticEvent,
  NativeScrollEvent,
  TouchableOpacity,
  Modal,
  Pressable,
  Animated,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";
import {
  Bell,
  AlertTriangle,
  Info,
  Scissors,
  X,
} from "lucide-react-native";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { StoriesRow } from "@/components/StoriesRow";
import { BorodachLogo } from "@/components/BorodachLogo";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import type { CompanyStats, PeriodStats } from "@/lib/types";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const HEADER_AVATAR = 40;
const INFO_CARD_WIDTH = SCREEN_WIDTH - 60;
const SHOP_CARD_WIDTH = SCREEN_WIDTH - spacing.md * 2;

interface DashboardNotification {
  id: number;
  title: string;
  text: string;
  type: "info" | "warning";
  dismissible: boolean;
}

const MOCK_NOTIFICATIONS: DashboardNotification[] = [
  {
    id: 1,
    title: "Роялти за март",
    text: "Срок оплаты роялти до 5 апреля. Не забудьте произвести оплату вовремя.",
    type: "warning",
    dismissible: true,
  },
  {
    id: 2,
    title: "Новая акция для клиентов",
    text: "Подключите весеннюю акцию «Стрижка + уход» со скидкой 20% для привлечения новых клиентов.",
    type: "info",
    dismissible: true,
  },
  {
    id: 3,
    title: "Обновление приложения",
    text: "Скоро выйдет обновление с улучшенной статистикой.",
    type: "info",
    dismissible: true,
  },
];

function initialsFromName(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    const a = parts[0][0] ?? "";
    const b = parts[1][0] ?? "";
    return (a + b).toUpperCase();
  }
  if (parts.length === 1 && parts[0].length >= 2) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return "ВВ";
}

function rankArrow(change: number): string {
  if (change > 0) return `↑${change}`;
  if (change < 0) return `↓${Math.abs(change)}`;
  return "—";
}

function rankColor(change: number): string {
  if (change > 0) return colors.success;
  if (change < 0) return colors.danger;
  return colors.textMuted;
}

export default function DashboardScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const profile = useApi(() => api.getProfile());
  const todayStats = useApi(() => api.getStats("today"));
  const monthStats = useApi(() => api.getStats("current_month"));

  const [period, setPeriod] = useState<"month" | "today">("today");
  const cardFade = useRef(new Animated.Value(1)).current;

  const switchPeriod = useCallback(
    (next: "month" | "today") => {
      if (next === period) return;
      Animated.sequence([
        Animated.timing(cardFade, {
          toValue: 0,
          duration: 120,
          useNativeDriver: true,
        }),
        Animated.timing(cardFade, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start();
      setTimeout(() => setPeriod(next), 120);
    },
    [period, cardFade]
  );

  const [activeShopIndex, setActiveShopIndex] = useState(0);
  const [activeInfoIndex, setActiveInfoIndex] = useState(0);
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());
  const [detail, setDetail] = useState<DashboardNotification | null>(null);

  const onShopScroll = useCallback(
    (e: NativeSyntheticEvent<NativeScrollEvent>) => {
      const x = e.nativeEvent.contentOffset.x;
      const idx = Math.round(x / SCREEN_WIDTH);
      setActiveShopIndex(idx);
    },
    []
  );

  const onInfoScroll = useCallback(
    (e: NativeSyntheticEvent<NativeScrollEvent>) => {
      const x = e.nativeEvent.contentOffset.x;
      const idx = Math.round(x / (INFO_CARD_WIDTH + 12));
      setActiveInfoIndex(idx);
    },
    []
  );

  if (profile.loading && !profile.data) return <LoadingScreen />;
  if (profile.error) {
    return (
      <ErrorMessage message={profile.error} onRetry={profile.refresh} />
    );
  }

  const p = profile.data!;
  const userInitials = initialsFromName(p.full_name);

  const primaryStats: PeriodStats | null =
    period === "month" ? monthStats.data : todayStats.data;
  const cards: CompanyStats[] = primaryStats?.companies ?? [];

  const visibleNotifications = MOCK_NOTIFICATIONS.filter(
    (n) => !dismissed.has(n.id)
  );
  const warnings = visibleNotifications.filter((n) => n.type === "warning");
  const infos = visibleNotifications.filter((n) => n.type === "info");
  const hasUnreadBellDot = visibleNotifications.length > 0;

  const isLoading =
    profile.loading || todayStats.loading || monthStats.loading;

  function dismissNotification(id: number) {
    setDismissed((prev) => new Set(prev).add(id));
  }

  const revenueSubtitle =
    period === "month" ? "выручка за месяц" : "выручка за сегодня";

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <ScrollView
        style={styles.screen}
        contentContainerStyle={[
          styles.content,
          { paddingBottom: 100 + insets.bottom },
        ]}
        refreshControl={
          <RefreshControl
            refreshing={isLoading}
            onRefresh={() => {
              profile.refresh();
              todayStats.refresh();
              monthStats.refresh();
            }}
            tintColor={colors.accent}
          />
        }
      >
        <View
          style={[
            styles.header,
            { paddingTop: insets.top + spacing.sm },
          ]}
        >
          <TouchableOpacity
            style={styles.avatarGreen}
            activeOpacity={0.7}
            onPress={() => router.push("/profile-screen")}
            accessibilityRole="button"
            accessibilityLabel="Профиль"
          >
            <Text style={styles.avatarInitials}>{userInitials}</Text>
          </TouchableOpacity>
          <View style={styles.logoWrap}>
            <BorodachLogo width={132} height={HEADER_AVATAR} color={colors.text} />
          </View>
          <TouchableOpacity
            style={styles.bellWrap}
            activeOpacity={0.7}
            onPress={() => router.push({ pathname: "/notifications" })}
            accessibilityRole="button"
            accessibilityLabel="Уведомления"
          >
            <Bell size={20} color={colors.text} strokeWidth={2} />
            {hasUnreadBellDot && <View style={styles.bellDot} />}
          </TouchableOpacity>
        </View>

        <StoriesRow />

        {warnings.map((item) => (
          <View key={item.id} style={styles.warningOuter}>
            <TouchableOpacity
              style={styles.warningCard}
              activeOpacity={0.85}
              onPress={() => setDetail(item)}
            >
              <AlertTriangle
                size={20}
                color="#996B00"
                strokeWidth={2}
                style={styles.bannerIcon}
              />
              <View style={styles.bannerTextWrap}>
                <Text style={styles.warningTitle}>{item.title}</Text>
                <Text style={styles.warningBody}>{item.text}</Text>
              </View>
              {item.dismissible && (
                <TouchableOpacity
                  style={styles.dismissBtn}
                  onPress={() => dismissNotification(item.id)}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <X size={18} color={colors.textMuted} strokeWidth={2} />
                </TouchableOpacity>
              )}
            </TouchableOpacity>
          </View>
        ))}

        {infos.length > 0 && (
          <View style={styles.infoSection}>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              onScroll={onInfoScroll}
              scrollEventThrottle={16}
              decelerationRate="fast"
              snapToInterval={INFO_CARD_WIDTH + 12}
              snapToAlignment="start"
              contentContainerStyle={{ paddingHorizontal: spacing.md, gap: 12 }}
            >
              {infos.map((item) => (
                <TouchableOpacity
                  key={item.id}
                  style={[styles.infoCard, { width: INFO_CARD_WIDTH }]}
                  activeOpacity={0.85}
                  onPress={() => setDetail(item)}
                >
                  <Info
                    size={20}
                    color={colors.infoIcon}
                    strokeWidth={2}
                    style={styles.bannerIcon}
                  />
                  <View style={styles.bannerTextWrap}>
                    <Text style={styles.infoTitle}>{item.title}</Text>
                    <Text style={styles.infoBody}>{item.text}</Text>
                  </View>
                  {item.dismissible && (
                    <TouchableOpacity
                      style={styles.dismissBtn}
                      onPress={() => dismissNotification(item.id)}
                      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                    >
                      <X size={18} color={colors.textMuted} strokeWidth={2} />
                    </TouchableOpacity>
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
            {infos.length > 1 && (
              <View style={styles.dots}>
                {infos.map((_, idx) => (
                  <View
                    key={idx}
                    style={[
                      styles.dot,
                      idx === activeInfoIndex && styles.dotActive,
                    ]}
                  />
                ))}
              </View>
            )}
          </View>
        )}

        {cards.length > 0 && (
          <View style={styles.shopSection}>
            <ScrollView
              horizontal
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              onScroll={onShopScroll}
              scrollEventThrottle={16}
              decelerationRate="fast"
            >
              {cards.map((company, idx) => {
                return (
                  <View
                    key={company.yclients_id ?? idx}
                    style={styles.shopPage}
                  >
                    <Text style={styles.shopHeaderName} numberOfLines={2}>
                      {company.name}
                    </Text>
                    <View style={[styles.shopCard, { width: SHOP_CARD_WIDTH }]}>
                    <View style={styles.shopTopRow}>
                      <View style={styles.shopIconCircle}>
                        <Scissors
                          size={20}
                          color={colors.white}
                          strokeWidth={2}
                        />
                      </View>
                      <View style={{ flex: 1 }} />
                      <View style={styles.periodChips}>
                        <TouchableOpacity
                          style={[
                            styles.periodChip,
                            period === "today" && styles.periodChipActive,
                          ]}
                          onPress={() => switchPeriod("today")}
                          activeOpacity={0.7}
                        >
                          <Text
                            style={[
                              styles.periodChipText,
                              period === "today" && styles.periodChipTextActive,
                            ]}
                          >
                            Сегодня
                          </Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                          style={[
                            styles.periodChip,
                            period === "month" && styles.periodChipActive,
                          ]}
                          onPress={() => switchPeriod("month")}
                          activeOpacity={0.7}
                        >
                          <Text
                            style={[
                              styles.periodChipText,
                              period === "month" && styles.periodChipTextActive,
                            ]}
                          >
                            Месяц
                          </Text>
                        </TouchableOpacity>
                      </View>
                    </View>

                    <Animated.View style={{ opacity: cardFade }}>
                    <View style={styles.revenueBlock}>
                      <Text style={styles.revenueValue}>
                        {formatCurrency(company.revenue)}
                      </Text>
                      <Text style={styles.revenueLabel}>{revenueSubtitle}</Text>
                    </View>

                    <View style={styles.metricsRow}>
                      <View style={styles.metric}>
                        <Text style={styles.metricValue}>
                          {formatNumber(company.completed_count)}
                        </Text>
                        <Text style={styles.metricLabel}>записей</Text>
                      </View>
                      <View style={styles.metricDivider} />
                      <View style={styles.metric}>
                        <Text style={styles.metricValue}>
                          {formatCurrency(company.avg_check)}
                        </Text>
                        <Text style={styles.metricLabel}>ср. чек</Text>
                      </View>
                      <View style={styles.metricDivider} />
                      <View style={styles.metric}>
                        <Text style={styles.metricValue}>
                          #{company.rank}
                        </Text>
                        <Text
                          style={[
                            styles.metricLabel,
                            { color: rankColor(company.rank_change) },
                          ]}
                        >
                          {rankArrow(company.rank_change)}
                        </Text>
                      </View>
                    </View>
                    </Animated.View>
                    </View>
                  </View>
                );
              })}
            </ScrollView>
            {cards.length > 1 && (
              <View style={styles.dots}>
                {cards.map((_, idx) => (
                  <View
                    key={idx}
                    style={[
                      styles.dot,
                      idx === activeShopIndex && styles.dotActive,
                    ]}
                  />
                ))}
              </View>
            )}
          </View>
        )}

        {cards.length === 0 && !isLoading && (
          <View style={styles.padded}>
            <View style={styles.emptyCard}>
              <Text style={styles.emptyText}>Нет данных</Text>
            </View>
          </View>
        )}
      </ScrollView>

      <Modal
        visible={detail !== null}
        animationType="slide"
        transparent
        onRequestClose={() => setDetail(null)}
      >
        <View style={styles.modalRoot}>
          <Pressable style={styles.modalBackdrop} onPress={() => setDetail(null)} />
          <View style={[styles.modalSheet, { paddingBottom: insets.bottom + spacing.lg }]}>
            <View style={styles.modalHandle} />
            {detail && (
              <>
                <View
                  style={[
                    styles.modalIconCircle,
                    detail.type === "warning"
                      ? styles.modalIconWarning
                      : styles.modalIconInfo,
                  ]}
                >
                  {detail.type === "warning" ? (
                    <AlertTriangle size={36} color="#996B00" strokeWidth={2} />
                  ) : (
                    <Info size={36} color={colors.infoIcon} strokeWidth={2} />
                  )}
                </View>
                <Text style={styles.modalTitle}>{detail.title}</Text>
                <Text style={styles.modalText}>{detail.text}</Text>
                <TouchableOpacity
                  style={styles.modalButton}
                  activeOpacity={0.85}
                  onPress={() => setDetail(null)}
                >
                  <Text style={styles.modalButtonText}>Понятно</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    gap: spacing.md,
    paddingTop: 0,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.md,
    marginBottom: spacing.xs,
  },
  avatarGreen: {
    width: HEADER_AVATAR,
    height: HEADER_AVATAR,
    borderRadius: HEADER_AVATAR / 2,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarInitials: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.white,
  },
  logoWrap: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  bellWrap: {
    width: HEADER_AVATAR,
    height: HEADER_AVATAR,
    borderRadius: HEADER_AVATAR / 2,
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 4,
  },
  bellDot: {
    position: "absolute",
    top: 8,
    right: 8,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.danger,
    borderWidth: 1.5,
    borderColor: colors.white,
  },

  warningOuter: {
    paddingHorizontal: spacing.md,
  },
  warningCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: colors.warningBg,
    borderRadius: radius.md,
    borderWidth: 0.5,
    borderColor: colors.warningBorder,
    padding: spacing.md,
  },
  warningTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#996B00",
    marginBottom: 3,
  },
  warningBody: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },

  infoSection: {
    marginBottom: spacing.xs,
  },
  infoCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: colors.infoBg,
    borderRadius: radius.md,
    borderWidth: 0.5,
    borderColor: colors.infoBorder,
    padding: spacing.md,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#1A5CBA",
    marginBottom: 3,
  },
  infoBody: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  bannerIcon: {
    marginTop: 1,
    marginRight: spacing.sm,
  },
  bannerTextWrap: {
    flex: 1,
  },
  dismissBtn: {
    padding: 2,
    marginLeft: spacing.xs,
  },

  shopSection: {},
  shopPage: {
    width: SCREEN_WIDTH,
    alignItems: "center",
    paddingVertical: spacing.xs,
  },
  shopCard: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginRight: 0,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  shopHeaderName: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.text,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
    width: SHOP_CARD_WIDTH,
    lineHeight: 22,
    textAlign: "left",
  },
  shopIconCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  shopTopRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  periodChips: {
    flexDirection: "row",
    gap: 4,
  },
  periodChip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "transparent",
    backgroundColor: colors.cardAlt,
  },
  periodChipActive: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  periodChipText: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  periodChipTextActive: {
    color: colors.accent,
  },
  revenueBlock: {
    alignItems: "center",
    marginBottom: spacing.md,
    paddingBottom: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  revenueValue: {
    fontSize: 36,
    fontWeight: "700",
    color: colors.accent,
  },
  revenueLabel: {
    ...fonts.caption,
    marginTop: spacing.xs,
    textAlign: "center",
  },
  metricsRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  metric: {
    flex: 1,
    alignItems: "center",
  },
  metricValue: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.text,
  },
  metricLabel: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 2,
  },
  metricDivider: {
    width: StyleSheet.hairlineWidth,
    height: 28,
    backgroundColor: colors.border,
  },

  dots: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 6,
    marginTop: spacing.sm,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.border,
  },
  dotActive: {
    backgroundColor: colors.accent,
    width: 18,
    borderRadius: 3,
  },

  padded: {
    paddingHorizontal: spacing.md,
  },
  emptyCard: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: spacing.lg,
  },
  emptyText: {
    ...fonts.regular,
    color: colors.textMuted,
    textAlign: "center",
  },

  modalRoot: {
    flex: 1,
    justifyContent: "flex-end",
  },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.45)",
  },
  modalSheet: {
    backgroundColor: colors.card,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  modalHandle: {
    alignSelf: "center",
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.border,
    marginBottom: spacing.lg,
  },
  modalIconCircle: {
    width: 88,
    height: 88,
    borderRadius: 44,
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "center",
    marginBottom: spacing.lg,
  },
  modalIconWarning: {
    backgroundColor: colors.warningBg,
  },
  modalIconInfo: {
    backgroundColor: colors.infoBg,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: colors.text,
    textAlign: "center",
    marginBottom: spacing.sm,
  },
  modalText: {
    ...fonts.regular,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 20,
    marginBottom: spacing.lg,
  },
  modalButton: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: "center",
  },
  modalButtonText: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.white,
  },
});
