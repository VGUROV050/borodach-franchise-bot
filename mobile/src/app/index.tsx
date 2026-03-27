import React from "react";
import { ScrollView, View, Text, StyleSheet, RefreshControl } from "react-native";
import { Card } from "@/components/ui/Card";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import { formatCurrency } from "@/lib/formatters";

export default function DashboardScreen() {
  const profile = useApi(() => api.getProfile());
  const stats = useApi(() => api.getStats("current_month"));

  if (profile.loading && !profile.data) return <LoadingScreen />;
  if (profile.error) return <ErrorMessage message={profile.error} onRetry={profile.refresh} />;

  const p = profile.data!;
  const s = stats.data;

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={profile.loading || stats.loading}
          onRefresh={() => {
            profile.refresh();
            stats.refresh();
          }}
          tintColor={colors.accent}
        />
      }
    >
      <View style={styles.greeting}>
        <Text style={styles.hello}>Здравствуйте,</Text>
        <Text style={styles.name}>{p.full_name} 👋</Text>
      </View>

      {s && (
        <Card variant="accent" style={styles.revenueCard}>
          <Text style={styles.revenueLabel}>Выручка за текущий месяц</Text>
          <Text style={styles.revenueValue}>{formatCurrency(s.total_revenue)}</Text>
          <Text style={styles.revenuePeriod}>{s.period_label}</Text>
          <View style={styles.revenueMeta}>
            <View style={styles.metaItem}>
              <Text style={styles.metaValue}>{s.total_completed}</Text>
              <Text style={styles.metaLabel}>записей</Text>
            </View>
            <View style={styles.metaItem}>
              <Text style={styles.metaValue}>{s.companies.length}</Text>
              <Text style={styles.metaLabel}>салонов</Text>
            </View>
          </View>
        </Card>
      )}

      <Text style={styles.sectionTitle}>Ваши салоны</Text>
      {p.companies.length === 0 ? (
        <Card>
          <Text style={styles.emptyText}>Нет привязанных салонов</Text>
        </Card>
      ) : (
        p.companies.map((c) => (
          <Card key={c.id} style={styles.companyCard}>
            <Text style={styles.companyName}>💈 {c.name}</Text>
            {c.city && (
              <Text style={styles.companyCity}>{c.city}</Text>
            )}
          </Card>
        ))
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
    padding: spacing.md,
    gap: spacing.md,
    paddingBottom: 100,
  },
  greeting: {
    marginBottom: spacing.sm,
  },
  hello: {
    ...fonts.regular,
    color: colors.textSecondary,
  },
  name: {
    ...fonts.title,
  },
  revenueCard: {
    alignItems: "center",
    paddingVertical: spacing.lg,
  },
  revenueLabel: {
    ...fonts.caption,
    marginBottom: spacing.xs,
  },
  revenueValue: {
    fontSize: 32,
    fontWeight: "800",
    color: colors.accent,
  },
  revenuePeriod: {
    ...fonts.caption,
    marginTop: spacing.xs,
  },
  revenueMeta: {
    flexDirection: "row",
    gap: spacing.xl,
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  metaItem: {
    alignItems: "center",
  },
  metaValue: {
    ...fonts.large,
    color: colors.accentLight,
  },
  metaLabel: {
    ...fonts.caption,
  },
  sectionTitle: {
    ...fonts.large,
    marginTop: spacing.sm,
  },
  companyCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  companyName: {
    ...fonts.medium,
    fontWeight: "600",
  },
  companyCity: {
    ...fonts.caption,
  },
  emptyText: {
    ...fonts.regular,
    color: colors.textMuted,
    textAlign: "center",
  },
});
