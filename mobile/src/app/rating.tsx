import React, { useState } from "react";
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from "react-native";
import { RatingTable } from "@/components/rating/RatingTable";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import type { RatingPeriod } from "@/lib/types";

export default function RatingScreen() {
  const [period, setPeriod] = useState<RatingPeriod>("current");
  const { data, loading, error, refresh } = useApi(
    () => api.getRating(period),
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
          tintColor={colors.accent}
        />
      }
    >
      <View style={styles.toggle}>
        <TouchableOpacity
          style={[styles.toggleBtn, period === "current" && styles.toggleActive]}
          onPress={() => setPeriod("current")}
        >
          <Text style={[styles.toggleText, period === "current" && styles.toggleTextActive]}>
            Текущий месяц
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleBtn, period === "previous" && styles.toggleActive]}
          onPress={() => setPeriod("previous")}
        >
          <Text style={[styles.toggleText, period === "previous" && styles.toggleTextActive]}>
            Прошлый месяц
          </Text>
        </TouchableOpacity>
      </View>

      {loading && !data ? (
        <LoadingScreen />
      ) : error ? (
        <ErrorMessage message={error} onRetry={refresh} />
      ) : data ? (
        <>
          <Text style={styles.periodLabel}>🏆 {data.period_label}</Text>
          <RatingTable
            entries={data.entries}
            partnerRanks={data.partner_ranks}
            totalCompanies={data.total_companies}
          />
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
    padding: spacing.md,
    paddingBottom: 100,
    gap: spacing.md,
  },
  toggle: {
    flexDirection: "row",
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: 4,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: spacing.sm,
    alignItems: "center",
    borderRadius: radius.sm,
  },
  toggleActive: {
    backgroundColor: colors.accent,
  },
  toggleText: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "600",
  },
  toggleTextActive: {
    color: colors.white,
  },
  periodLabel: {
    ...fonts.large,
    textAlign: "center",
  },
});
