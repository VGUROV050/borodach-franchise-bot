import React from "react";
import { ScrollView, View, Text, StyleSheet, RefreshControl } from "react-native";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts } from "@/lib/theme";
import { formatDate } from "@/lib/formatters";
import { Stack } from "expo-router";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  verified: { label: "Верифицирован", color: colors.success },
  pending: { label: "На проверке", color: colors.warning },
  rejected: { label: "Отклонён", color: colors.danger },
};

export default function ProfileScreen() {
  const { data, loading, error, refresh } = useApi(() => api.getProfile());

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorMessage message={error} onRetry={refresh} />;

  const p = data!;
  const statusInfo = STATUS_LABELS[p.status] ?? {
    label: p.status,
    color: colors.textMuted,
  };

  return (
    <>
      <Stack.Screen options={{ headerTitle: "Профиль" }} />
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={refresh}
            tintColor={colors.accent}
          />
        }
      >
        <View style={styles.header}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {p.full_name.charAt(0).toUpperCase()}
            </Text>
          </View>
          <Text style={styles.name}>{p.full_name}</Text>
          <Badge label={statusInfo.label} bgColor={statusInfo.color} />
        </View>

        <Card>
          <InfoRow label="Телефон" value={p.phone_masked} />
          <InfoRow
            label="Роль"
            value={p.is_owner ? "Владелец" : (p.position ?? "Сотрудник")}
          />
          <InfoRow label="Регистрация" value={formatDate(p.created_at)} />
          {p.verified_at && (
            <InfoRow
              label="Верификация"
              value={formatDate(p.verified_at)}
              last
            />
          )}
        </Card>

        <Text style={styles.sectionTitle}>Салоны</Text>
        {p.companies.length === 0 ? (
          <Card>
            <Text style={styles.emptyText}>Нет привязанных салонов</Text>
          </Card>
        ) : (
          p.companies.map((c) => (
            <Card key={c.id}>
              <Text style={styles.companyName}>💈 {c.name}</Text>
              {c.city && <Text style={styles.companyDetail}>{c.city}</Text>}
              {c.region && <Text style={styles.companyDetail}>{c.region}</Text>}
            </Card>
          ))
        )}

        <Text style={styles.version}>v0.1.0 — TestFlight MVP</Text>
      </ScrollView>
    </>
  );
}

function InfoRow({
  label,
  value,
  last,
}: {
  label: string;
  value: string;
  last?: boolean;
}) {
  return (
    <View style={[styles.infoRow, !last && styles.infoRowBorder]}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
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
  header: {
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.lg,
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: {
    fontSize: 32,
    fontWeight: "800",
    color: colors.white,
  },
  name: {
    ...fonts.title,
  },
  sectionTitle: {
    ...fonts.large,
    marginTop: spacing.sm,
  },
  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: spacing.sm,
  },
  infoRowBorder: {
    borderBottomWidth: 0.5,
    borderBottomColor: colors.border,
  },
  infoLabel: {
    ...fonts.regular,
    color: colors.textSecondary,
  },
  infoValue: {
    ...fonts.regular,
    fontWeight: "600",
  },
  companyName: {
    ...fonts.medium,
    fontWeight: "600",
  },
  companyDetail: {
    ...fonts.caption,
    marginTop: 2,
  },
  emptyText: {
    ...fonts.regular,
    color: colors.textMuted,
    textAlign: "center",
  },
  version: {
    ...fonts.caption,
    textAlign: "center",
    marginTop: spacing.lg,
    color: colors.textMuted,
  },
});
