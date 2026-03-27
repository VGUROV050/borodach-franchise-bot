import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Card } from "@/components/ui/Card";
import { colors, spacing, fonts } from "@/lib/theme";
import { formatCurrency, rankChangeText, rankChangeColor } from "@/lib/formatters";
import type { RatingEntry } from "@/lib/types";

interface RatingRowProps {
  entry: RatingEntry;
}

function medal(rank: number): string {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return `${rank}.`;
}

export function RatingRow({ entry }: RatingRowProps) {
  return (
    <Card variant={entry.is_partner ? "accent" : "default"} style={styles.card}>
      <View style={styles.row}>
        <Text style={styles.rank}>{medal(entry.rank)}</Text>
        <View style={styles.info}>
          <Text style={[styles.name, entry.is_partner && styles.namePartner]}>
            {entry.is_partner ? `👉 ${entry.company_name}` : entry.company_name}
          </Text>
          <Text style={styles.location}>{entry.location}</Text>
        </View>
        <View style={styles.right}>
          <Text style={styles.revenue}>{formatCurrency(entry.revenue)}</Text>
          {entry.rank_change !== 0 && (
            <Text style={[styles.change, { color: rankChangeColor(entry.rank_change) }]}>
              {rankChangeText(entry.rank_change)}
            </Text>
          )}
        </View>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
  },
  rank: {
    fontSize: 18,
    width: 40,
    textAlign: "center",
  },
  info: {
    flex: 1,
    marginLeft: spacing.sm,
  },
  name: {
    ...fonts.regular,
  },
  namePartner: {
    fontWeight: "700",
    color: colors.accentLight,
  },
  location: {
    ...fonts.caption,
    marginTop: 1,
  },
  right: {
    alignItems: "flex-end",
  },
  revenue: {
    ...fonts.regular,
    fontWeight: "600",
    color: colors.text,
  },
  change: {
    fontSize: 12,
    fontWeight: "700",
    marginTop: 2,
  },
});
