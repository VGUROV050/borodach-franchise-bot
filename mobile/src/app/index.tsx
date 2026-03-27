import React, { useRef, useState, useCallback } from "react";
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
  Animated,
} from "react-native";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { StoriesRow } from "@/components/StoriesRow";
import { NotificationBanners } from "@/components/NotificationBanners";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import type { CompanyStats, Company, PeriodStats } from "@/lib/types";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const CARD_MARGIN = spacing.md;
const CARD_WIDTH = SCREEN_WIDTH - CARD_MARGIN * 2;

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

function findCity(
  companies: Company[],
  yclientsId: string | null
): string | null {
  if (!yclientsId) return null;
  const match = companies.find((c) => c.yclients_id === yclientsId);
  return match?.city ?? null;
}

function findCompanyInPeriod(
  stats: PeriodStats | undefined,
  yclientsId: string | null
): CompanyStats | null {
  if (!stats || !yclientsId) return null;
  return stats.companies.find((c) => c.yclients_id === yclientsId) ?? null;
}

export default function DashboardScreen() {
  const profile = useApi(() => api.getProfile());
  const todayStats = useApi(() => api.getStats("today"));
  const monthStats = useApi(() => api.getStats("current_month"));
  const [activeCard, setActiveCard] = useState(0);
  const [showMonth, setShowMonth] = useState(false);
  const flipAnim = useRef(new Animated.Value(1)).current;

  if (profile.loading && !profile.data) return <LoadingScreen />;
  if (profile.error)
    return (
      <ErrorMessage message={profile.error} onRetry={profile.refresh} />
    );

  const p = profile.data!;
  const primaryStats = showMonth ? monthStats.data : todayStats.data;
  const cards: CompanyStats[] = primaryStats?.companies ?? [];

  function togglePeriod() {
    Animated.timing(flipAnim, {
      toValue: 0,
      duration: 120,
      useNativeDriver: true,
    }).start(() => {
      setShowMonth((prev) => !prev);
      Animated.timing(flipAnim, {
        toValue: 1,
        duration: 120,
        useNativeDriver: true,
      }).start();
    });
  }

  function onScroll(e: NativeSyntheticEvent<NativeScrollEvent>) {
    const x = e.nativeEvent.contentOffset.x;
    const idx = Math.round(x / CARD_WIDTH);
    setActiveCard(idx);
  }

  const isLoading =
    profile.loading || todayStats.loading || monthStats.loading;

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
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
      <View style={styles.greeting}>
        <Text style={styles.hello}>Здравствуйте,</Text>
        <Text style={styles.name}>{p.full_name} 👋</Text>
      </View>

      <StoriesRow />

      <NotificationBanners />

      {cards.length > 0 && (
        <Animated.View
          style={{
            opacity: flipAnim,
            transform: [
              {
                scaleX: flipAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.85, 1],
                }),
              },
            ],
          }}
        >
          <ScrollView
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onScroll={onScroll}
            scrollEventThrottle={16}
            decelerationRate="fast"
            snapToInterval={CARD_WIDTH}
            snapToAlignment="start"
            contentContainerStyle={styles.carouselContent}
          >
            {cards.map((company, idx) => {
              const city = findCity(p.companies, company.yclients_id);
              return (
                <View
                  key={company.yclients_id ?? idx}
                  style={styles.shopCard}
                >
                  <View style={styles.shopHeader}>
                    <Text style={styles.shopEmoji}>💈</Text>
                    <View style={styles.shopNameWrap}>
                      <Text style={styles.shopName} numberOfLines={2}>
                        {company.name}
                      </Text>
                      {city && (
                        <Text style={styles.shopCity}>{city}</Text>
                      )}
                    </View>
                    <TouchableOpacity
                      style={styles.periodBtn}
                      activeOpacity={0.7}
                      onPress={togglePeriod}
                    >
                      <Text style={styles.periodBtnText}>
                        {showMonth ? "сегодня" : "месяц"}
                      </Text>
                    </TouchableOpacity>
                  </View>

                  <View style={styles.revenueBlock}>
                    <Text style={styles.revenueValue}>
                      {formatCurrency(company.revenue)}
                    </Text>
                    <Text style={styles.revenuePeriod}>
                      {primaryStats!.period_label}
                    </Text>
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
                    idx === activeCard && styles.dotActive,
                  ]}
                />
              ))}
            </View>
          )}
        </Animated.View>
      )}

      {cards.length === 0 && !isLoading && (
        <View style={styles.padded}>
          <View style={styles.emptyCard}>
            <Text style={styles.emptyText}>Нет данных</Text>
          </View>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    gap: spacing.md,
    paddingBottom: 100,
    paddingTop: spacing.sm,
  },
  greeting: {
    paddingHorizontal: spacing.md,
    marginBottom: spacing.xs,
  },
  hello: {
    ...fonts.regular,
    color: colors.textSecondary,
  },
  name: {
    ...fonts.title,
  },
  padded: {
    paddingHorizontal: spacing.md,
  },

  carouselContent: {
    paddingHorizontal: CARD_MARGIN,
  },
  shopCard: {
    width: CARD_WIDTH,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.lg,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  shopHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  shopEmoji: {
    fontSize: 28,
    marginTop: 2,
  },
  shopNameWrap: {
    flex: 1,
  },
  shopName: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.text,
    lineHeight: 20,
  },
  shopCity: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  periodBtn: {
    backgroundColor: colors.accentBg,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: radius.sm,
  },
  periodBtnText: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.accent,
  },

  revenueBlock: {
    alignItems: "center",
    marginBottom: spacing.md,
    paddingBottom: spacing.md,
    borderBottomWidth: 0.5,
    borderBottomColor: colors.border,
  },
  revenueValue: {
    fontSize: 30,
    fontWeight: "800",
    color: colors.accent,
  },
  revenuePeriod: {
    ...fonts.caption,
    marginTop: spacing.xs,
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
    width: 0.5,
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
});
