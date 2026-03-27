import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { colors, spacing, fonts } from "@/lib/theme";
import { formatCurrency, rankChangeText, rankChangeColor } from "@/lib/formatters";
import type { CompanyStats } from "@/lib/types";

interface StatsCardProps {
  stats: CompanyStats;
  isHighlighted?: boolean;
}

export function StatsCard({ stats, isHighlighted }: StatsCardProps) {
  if (stats.error) {
    return (
      <Card variant={isHighlighted ? "accent" : "default"}>
        <Text style={styles.name}>💈 {stats.name}</Text>
        <Text style={styles.errorText}>❌ {stats.error}</Text>
      </Card>
    );
  }

  return (
    <Card variant={isHighlighted ? "accent" : "default"}>
      <Text style={styles.name}>💈 {stats.name}</Text>

      <View style={styles.row}>
        <View style={styles.metric}>
          <Text style={styles.metricLabel}>Выручка</Text>
          <Text style={styles.metricValue}>{formatCurrency(stats.revenue)}</Text>
        </View>
        <View style={styles.metric}>
          <Text style={styles.metricLabel}>Записи</Text>
          <Text style={styles.metricValue}>
            {stats.completed_count}/{stats.total_count}
          </Text>
        </View>
      </View>

      {stats.rank > 0 && (
        <View style={styles.rankRow}>
          <View style={styles.metric}>
            <Text style={styles.metricLabel}>Рейтинг</Text>
            <View style={styles.rankValueRow}>
              <Text style={styles.metricValue}>
                #{stats.rank} из {stats.total_companies}
              </Text>
              {stats.rank_change !== 0 && (
                <Badge
                  label={rankChangeText(stats.rank_change)}
                  bgColor={rankChangeColor(stats.rank_change)}
                />
              )}
            </View>
          </View>
          {stats.avg_check > 0 && (
            <View style={styles.metric}>
              <Text style={styles.metricLabel}>Ср. чек</Text>
              <Text style={styles.metricValue}>
                {formatCurrency(stats.avg_check)}
              </Text>
            </View>
          )}
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  name: {
    ...fonts.medium,
    fontWeight: "600",
    marginBottom: spacing.md,
  },
  row: {
    flexDirection: "row",
    gap: spacing.lg,
  },
  rankRow: {
    flexDirection: "row",
    gap: spacing.lg,
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  rankValueRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  metric: {
    flex: 1,
  },
  metricLabel: {
    ...fonts.caption,
    marginBottom: 2,
  },
  metricValue: {
    ...fonts.medium,
    fontWeight: "700",
    color: colors.accentLight,
  },
  errorText: {
    color: colors.danger,
    fontSize: 13,
  },
});
