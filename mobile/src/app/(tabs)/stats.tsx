// Statistics screen — per-barbershop revenue with period selector

import React, { useState } from "react";
import { ScrollView, View, Text, StyleSheet, RefreshControl } from "react-native";
import { Card } from "@/components/ui/Card";
import { StatsCard } from "@/components/stats/StatsCard";
import { PeriodSelector } from "@/components/stats/PeriodSelector";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts } from "@/lib/theme";
import { formatCurrency } from "@/lib/formatters";
import type { StatsPeriod } from "@/lib/types";

export default function StatsScreen() {
  const [period, setPeriod] = useState<StatsPeriod>("current_month");
  const { data, loading, error, refresh } = useApi(
    () => api.getStats(period),
    [period],
  );

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={loading && !!data}
          onRefresh={refresh}
          tintColor={colors.gold}
        />
      }
    >
      <PeriodSelector selected={period} onSelect={setPeriod} />

      {loading && !data ? (
        <LoadingScreen />
      ) : error ? (
        <ErrorMessage message={error} onRetry={refresh} />
      ) : data ? (
        <>
          <View style={styles.header}>
            <Text style={styles.periodLabel}>{data.period_label}</Text>
          </View>

          {data.companies.map((c, idx) => (
            <StatsCard key={c.yclients_id ?? idx} stats={c} />
          ))}

          {data.companies.length > 1 && data.total_revenue > 0 && (
            <Card variant="accent" style={styles.totalCard}>
              <Text style={styles.totalLabel}>Итого</Text>
              <Text style={styles.totalValue}>
                {formatCurrency(data.total_revenue)}
              </Text>
              <Text style={styles.totalRecords}>
                Завершено записей: {data.total_completed}
              </Text>
            </Card>
          )}
        </>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.xl,
    gap: spacing.md,
  },
  header: {
    alignItems: "center",
    paddingVertical: spacing.sm,
  },
  periodLabel: {
    ...fonts.caption,
  },
  totalCard: {
    alignItems: "center",
    paddingVertical: spacing.lg,
  },
  totalLabel: {
    ...fonts.caption,
    marginBottom: spacing.xs,
  },
  totalValue: {
    fontSize: 28,
    fontWeight: "800",
    color: colors.gold,
  },
  totalRecords: {
    ...fonts.caption,
    marginTop: spacing.xs,
  },
});
