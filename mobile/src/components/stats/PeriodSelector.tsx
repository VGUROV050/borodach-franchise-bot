import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from "react-native";
import { colors, spacing, radius } from "@/lib/theme";
import type { StatsPeriod } from "@/lib/types";

interface PeriodSelectorProps {
  selected: StatsPeriod;
  onSelect: (period: StatsPeriod) => void;
}

const PERIODS: { key: StatsPeriod; label: string }[] = [
  { key: "today", label: "Сегодня" },
  { key: "yesterday", label: "Вчера" },
  { key: "current_month", label: "Текущий месяц" },
  { key: "prev_month", label: "Прошлый месяц" },
];

export function PeriodSelector({ selected, onSelect }: PeriodSelectorProps) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.container}
    >
      {PERIODS.map(({ key, label }) => (
        <TouchableOpacity
          key={key}
          style={[styles.chip, selected === key && styles.chipActive]}
          onPress={() => onSelect(key)}
        >
          <Text style={[styles.chipText, selected === key && styles.chipTextActive]}>
            {label}
          </Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.lg,
    backgroundColor: colors.card,
    borderWidth: 0.5,
    borderColor: colors.border,
  },
  chipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  chipText: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "600",
  },
  chipTextActive: {
    color: colors.white,
  },
});
