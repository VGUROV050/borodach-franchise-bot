import React, { useState } from "react";
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { BarChart3, ArrowUp, ArrowDown, Minus } from "lucide-react-native";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import { formatCurrency } from "@/lib/formatters";
import type { StatsPeriod, CompanyStats } from "@/lib/types";

const PERIODS: { key: StatsPeriod; label: string }[] = [
  { key: "today", label: "Сегодня" },
  { key: "yesterday", label: "Вчера" },
  { key: "current_month", label: "Месяц" },
  { key: "prev_month", label: "Пред. месяц" },
];

const ACCENT = "#5CAE5D";
const CHIP_ACTIVE_BG = "rgba(92, 174, 93, 0.1)";

function RankChangeIcon({ change }: { change: number }) {
  if (change > 0) {
    return <ArrowUp size={14} color={colors.success} strokeWidth={2.5} />;
  }
  if (change < 0) {
    return <ArrowDown size={14} color={colors.danger} strokeWidth={2.5} />;
  }
  return <Minus size={14} color={colors.textMuted} strokeWidth={2.5} />;
}

function SalonStatCard({ stats }: { stats: CompanyStats }) {
  if (stats.error) {
    return (
      <View style={styles.salonCard}>
        <Text style={styles.salonName}>{stats.name}</Text>
        <Text style={styles.errorText}>{stats.error}</Text>
      </View>
    );
  }

  const rankLabel =
    stats.rank > 0
      ? `#${stats.rank} из ${stats.total_companies}`
      : "—";

  return (
    <View style={styles.salonCard}>
      <Text style={styles.salonName}>{stats.name}</Text>

      <Text style={styles.revenueLabel}>выручка</Text>
      <Text style={styles.revenueValue}>{formatCurrency(stats.revenue)}</Text>

      <View style={styles.metricsRow}>
        <View style={styles.metricCol}>
          <Text style={styles.metricLabel}>Записи</Text>
          <Text style={styles.metricValue}>
            {stats.completed_count}/{stats.total_count}
          </Text>
        </View>
        <View style={styles.metricCol}>
          <Text style={styles.metricLabel}>Ср. чек</Text>
          <Text style={styles.metricValue}>
            {stats.avg_check > 0 ? formatCurrency(stats.avg_check) : "—"}
          </Text>
        </View>
        <View style={styles.metricCol}>
          <Text style={styles.metricLabel}>Рейтинг</Text>
          <View style={styles.rankValueRow}>
            <Text style={styles.metricValue}>{rankLabel}</Text>
            {stats.rank > 0 && <RankChangeIcon change={stats.rank_change} />}
          </View>
        </View>
      </View>
    </View>
  );
}

export default function StatsScreen() {
  const [period, setPeriod] = useState<StatsPeriod>("current_month");
  const { data, loading, error, refresh } = useApi(
    () => api.getStats(period),
    [period],
  );

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.titleRow}>
        <BarChart3 size={32} color={ACCENT} strokeWidth={2} />
        <Text style={styles.screenTitle}>Статистика</Text>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chipsScroll}
        style={styles.chipsRow}
      >
        {PERIODS.map(({ key, label }) => {
          const active = period === key;
          return (
            <TouchableOpacity
              key={key}
              style={[styles.chip, active && styles.chipActive]}
              onPress={() => setPeriod(key)}
              activeOpacity={0.85}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>
                {label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={loading && !!data}
            onRefresh={refresh}
            tintColor={colors.accent}
          />
        }
      >
        {loading && !data ? (
          <LoadingScreen />
        ) : error ? (
          <ErrorMessage message={error} onRetry={refresh} />
        ) : data ? (
          <>
            <Text style={styles.periodHint}>{data.period_label}</Text>

            {data.companies.map((c, idx) => (
              <SalonStatCard key={c.yclients_id ?? idx} stats={c} />
            ))}

            {data.companies.length > 1 && data.total_revenue > 0 && (
              <View style={styles.totalCard}>
                <Text style={styles.totalLabel}>Итого</Text>
                <Text style={styles.totalValue}>
                  {formatCurrency(data.total_revenue)}
                </Text>
                <Text style={styles.totalRecords}>
                  Завершено записей: {data.total_completed}
                </Text>
              </View>
            )}
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  screenTitle: {
    fontSize: 22,
    fontWeight: "600",
    color: colors.text,
  },
  chipsRow: {
    flexGrow: 0,
  },
  chipsScroll: {
    gap: 8,
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.md,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "transparent",
    backgroundColor: colors.cardAlt,
  },
  chipActive: {
    backgroundColor: CHIP_ACTIVE_BG,
    borderColor: ACCENT,
  },
  chipText: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  chipTextActive: {
    color: ACCENT,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: spacing.md,
    paddingBottom: 100,
    gap: spacing.md,
  },
  periodHint: {
    ...fonts.caption,
    textAlign: "center",
    marginBottom: spacing.xs,
  },
  salonCard: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: spacing.md,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  salonName: {
    fontSize: 17,
    fontWeight: "600",
    color: colors.text,
    marginBottom: spacing.md,
  },
  revenueLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    textTransform: "lowercase",
    marginBottom: spacing.xs,
  },
  revenueValue: {
    fontSize: 32,
    fontWeight: "700",
    color: ACCENT,
    marginBottom: spacing.md,
  },
  metricsRow: {
    flexDirection: "row",
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    paddingTop: spacing.md,
    gap: spacing.sm,
  },
  metricCol: {
    flex: 1,
  },
  metricLabel: {
    fontSize: 11,
    color: colors.textSecondary,
    marginBottom: 4,
  },
  metricValue: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.text,
  },
  rankValueRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    flexWrap: "wrap",
  },
  errorText: {
    color: colors.danger,
    fontSize: 13,
  },
  totalCard: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: spacing.lg,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  totalLabel: {
    ...fonts.caption,
    marginBottom: spacing.xs,
  },
  totalValue: {
    fontSize: 28,
    fontWeight: "800",
    color: colors.accent,
  },
  totalRecords: {
    ...fonts.caption,
    marginTop: spacing.xs,
  },
});
