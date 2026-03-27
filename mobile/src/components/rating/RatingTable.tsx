import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { RatingRow } from "./RatingRow";
import { colors, spacing, fonts } from "@/lib/theme";
import type { RatingEntry } from "@/lib/types";

interface RatingTableProps {
  entries: RatingEntry[];
  partnerRanks: number[];
  totalCompanies: number;
}

export function RatingTable({ entries, partnerRanks, totalCompanies }: RatingTableProps) {
  const rowsToShow = buildVisibleRows(entries, partnerRanks);

  return (
    <View style={styles.container}>
      <Text style={styles.meta}>
        Всего салонов: {totalCompanies}
      </Text>
      {rowsToShow.map((item, idx) => {
        if (item.type === "separator") {
          return (
            <Text key={`sep-${idx}`} style={styles.separator}>
              · · ·
            </Text>
          );
        }
        return <RatingRow key={item.entry!.yclients_company_id} entry={item.entry!} />;
      })}
    </View>
  );
}

type VisibleItem =
  | { type: "row"; entry: RatingEntry }
  | { type: "separator"; entry?: undefined };

function buildVisibleRows(entries: RatingEntry[], partnerRanks: number[]): VisibleItem[] {
  const show = new Set<number>();

  // Top 3
  [1, 2, 3].forEach((r) => show.add(r));

  // Partner positions ± 2
  for (const pr of partnerRanks) {
    for (let i = Math.max(1, pr - 2); i <= Math.min(entries.length, pr + 2); i++) {
      show.add(i);
    }
  }

  const result: VisibleItem[] = [];
  let prevRank = 0;

  for (const entry of entries) {
    if (!show.has(entry.rank)) continue;
    if (prevRank > 0 && entry.rank - prevRank > 1) {
      result.push({ type: "separator" });
    }
    result.push({ type: "row", entry });
    prevRank = entry.rank;
  }

  return result;
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.sm,
  },
  meta: {
    ...fonts.caption,
    textAlign: "center",
    marginBottom: spacing.sm,
  },
  separator: {
    textAlign: "center",
    color: colors.textMuted,
    fontSize: 16,
    letterSpacing: 4,
    paddingVertical: spacing.xs,
  },
});
