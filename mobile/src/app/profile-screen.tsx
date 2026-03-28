import React from "react";
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  RefreshControl,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { User, Info } from "lucide-react-native";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import { formatDate } from "@/lib/formatters";

const HEADER_ICON = 32;
const ACCENT = "#5CAE5D";
const PENDING_BG = "#E8F5E9";

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
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.header}>
        <User size={HEADER_ICON} color={ACCENT} strokeWidth={2} />
        <Text style={styles.headerTitle}>Профиль</Text>
      </View>
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
        {p.has_pending_branch && p.pending_branch_text ? (
          <View style={styles.pendingBanner}>
            <Info size={20} color={ACCENT} strokeWidth={2} />
            <Text style={styles.pendingText}>{p.pending_branch_text}</Text>
          </View>
        ) : null}

        <View style={styles.profileCard}>
          <InfoRow label="ФИО" value={p.full_name} />
          <InfoRow label="Статус" value={statusInfo.label} />
          <InfoRow label="Телефон" value={p.phone_masked} />
          <InfoRow
            label="Роль"
            value={p.is_owner ? "Владелец" : (p.position ?? "Сотрудник")}
          />
          <InfoRow
            label="Регистрация"
            value={formatDate(p.created_at)}
            last={!p.verified_at}
          />
          {p.verified_at ? (
            <InfoRow
              label="Верификация"
              value={formatDate(p.verified_at)}
              last
            />
          ) : null}
        </View>

        <Text style={styles.salonsTitle}>Салоны</Text>
        {p.companies.length === 0 ? (
          <View style={styles.salonCard}>
            <Text style={styles.emptyText}>Нет привязанных салонов</Text>
          </View>
        ) : (
          p.companies.map((c) => (
            <View key={c.id} style={styles.salonCard}>
              <Text style={styles.companyName}>{c.name}</Text>
              {c.city ? (
                <Text style={styles.companyDetail}>{c.city}</Text>
              ) : null}
              {c.region ? (
                <Text style={styles.companyDetail}>{c.region}</Text>
              ) : null}
            </View>
          ))
        )}

        <Text style={styles.version}>v0.1.0 — TestFlight MVP</Text>
      </ScrollView>
    </SafeAreaView>
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
  safe: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: "600",
    color: colors.text,
  },
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    padding: spacing.md,
    gap: spacing.md,
    paddingBottom: 100,
  },
  pendingBanner: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    backgroundColor: PENDING_BG,
    borderWidth: 1,
    borderColor: ACCENT,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  pendingText: {
    ...fonts.regular,
    flex: 1,
    color: colors.text,
    lineHeight: 20,
  },
  profileCard: {
    backgroundColor: colors.white,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.06,
        shadowRadius: 8,
      },
      android: { elevation: 2 },
      default: {},
    }),
  },
  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: spacing.md,
    paddingVertical: spacing.md,
  },
  infoRowBorder: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  infoLabel: {
    ...fonts.regular,
    color: colors.textSecondary,
    flexShrink: 0,
  },
  infoValue: {
    ...fonts.regular,
    fontWeight: "500",
    color: colors.text,
    flex: 1,
    textAlign: "right",
  },
  salonsTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: colors.text,
    marginTop: spacing.xs,
  },
  salonCard: {
    backgroundColor: colors.white,
    borderRadius: radius.md,
    padding: spacing.md,
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.06,
        shadowRadius: 8,
      },
      android: { elevation: 2 },
      default: {},
    }),
  },
  companyName: {
    ...fonts.medium,
    fontWeight: "600",
    fontSize: 16,
  },
  companyDetail: {
    ...fonts.caption,
    marginTop: 4,
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
