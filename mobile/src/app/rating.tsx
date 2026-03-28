import React, { useMemo, useState } from "react";
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Trophy, ArrowUp, ArrowDown } from "lucide-react-native";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import {
  formatCurrency,
  formatNumber,
  rankChangeColor,
  rankChangeText,
} from "@/lib/formatters";
import type { RatingEntry, RatingPeriod } from "@/lib/types";

const TOGGLE_ACTIVE_BG = "rgba(92, 174, 93, 0.1)";
const INACTIVE_TOGGLE_BG = "#E5E5EA";
const ROW_BORDER = "#E5E5EA";

const MEDAL_FILL: Record<number, string> = {
  1: colors.gold,
  2: colors.silver,
  3: colors.bronze,
};

type VisibleItem =
  | { type: "row"; entry: RatingEntry }
  | { type: "separator" };

function buildVisibleRows(entries: RatingEntry[], partnerRanks: number[]): VisibleItem[] {
  const show = new Set<number>();

  [1, 2, 3].forEach((r) => show.add(r));

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

function RankChangeIndicator({ change }: { change: number }) {
  if (change === 0) {
    return null;
  }
  const color = rankChangeColor(change);
  const Icon = change > 0 ? ArrowUp : ArrowDown;
  return (
    <View style={styles.changeRow}>
      <Icon size={14} color={color} strokeWidth={2.5} />
      <Text style={[styles.changeText, { color }]}>{rankChangeText(change)}</Text>
    </View>
  );
}

function LeaderboardRow({
  entry,
  isLast,
}: {
  entry: RatingEntry;
  isLast: boolean;
}) {
  const medalColor = MEDAL_FILL[entry.rank];

  return (
    <View
      style={[
        styles.leaderRow,
        entry.is_partner && styles.leaderRowPartner,
        !isLast && styles.leaderRowBordered,
      ]}
    >
      <View style={styles.rankBlock}>
        <Text style={styles.rankText}>#{entry.rank}</Text>
        {entry.rank <= 3 && medalColor ? (
          <Trophy size={20} color={medalColor} fill={medalColor} strokeWidth={1.5} />
        ) : null}
      </View>

      <View style={styles.leaderMid}>
        <Text style={[styles.companyName, entry.is_partner && styles.companyNamePartner]} numberOfLines={2}>
          {entry.company_name}
        </Text>
        <Text style={styles.locationText} numberOfLines={2}>
          {entry.location}
        </Text>
      </View>

      <View style={styles.leaderRight}>
        <Text style={styles.revenueText}>{formatCurrency(entry.revenue)}</Text>
        <Text style={styles.avgCheckText}>{formatCurrency(entry.avg_check)}</Text>
        <RankChangeIndicator change={entry.rank_change} />
      </View>
    </View>
  );
}

export default function RatingScreen() {
  const [period, setPeriod] = useState<RatingPeriod>("current");
  const { data, loading, error, refresh } = useApi(
    () => api.getRating(period),
    [period],
  );

  const visibleItems = useMemo(() => {
    if (!data) return [];
    return buildVisibleRows(data.entries, data.partner_ranks);
  }, [data]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
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
        <View style={styles.header}>
          <Trophy size={32} color={colors.accent} strokeWidth={2} />
          <Text style={styles.headerTitle}>Рейтинг</Text>
        </View>

        <View style={styles.periodChips}>
          <TouchableOpacity
            style={[
              styles.periodChip,
              period === "current" && styles.periodChipActive,
            ]}
            onPress={() => setPeriod("current")}
            activeOpacity={0.7}
          >
            <Text
              style={[
                styles.periodChipText,
                period === "current" && styles.periodChipTextActive,
              ]}
            >
              Текущий
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.periodChip,
              period === "previous" && styles.periodChipActive,
            ]}
            onPress={() => setPeriod("previous")}
            activeOpacity={0.7}
          >
            <Text
              style={[
                styles.periodChipText,
                period === "previous" && styles.periodChipTextActive,
              ]}
            >
              Предыдущий
            </Text>
          </TouchableOpacity>
        </View>

        {loading && !data ? (
          <LoadingScreen />
        ) : error ? (
          <ErrorMessage message={error} onRetry={refresh} />
        ) : data ? (
          <>
            <View style={styles.metaRow}>
              <Text style={styles.periodLabel}>{data.period_label}</Text>
              <Text style={styles.metaLine}>
                {formatNumber(data.total_companies)} салонов
              </Text>
            </View>

            <View style={styles.card}>
              {visibleItems.map((item, idx) => {
                const last = idx === visibleItems.length - 1;
                if (item.type === "separator") {
                  return (
                    <View
                      key={`sep-${idx}`}
                      style={[styles.separatorRow, !last && styles.leaderRowBordered]}
                    >
                      <Text style={styles.separatorDots}>· · ·</Text>
                    </View>
                  );
                }
                return (
                  <LeaderboardRow
                    key={item.entry.yclients_company_id}
                    entry={item.entry}
                    isLast={last}
                  />
                );
              })}
            </View>
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
  screen: {
    flex: 1,
  },
  content: {
    paddingHorizontal: spacing.md,
    paddingBottom: 100,
    gap: spacing.md,
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
  periodChips: {
    flexDirection: "row",
    gap: 8,
  },
  periodChip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "transparent",
    backgroundColor: colors.cardAlt,
  },
  periodChipActive: {
    backgroundColor: TOGGLE_ACTIVE_BG,
    borderColor: colors.accent,
  },
  periodChipText: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  periodChipTextActive: {
    color: colors.accent,
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
  },
  periodLabel: {
    fontSize: 18,
    fontWeight: "600",
    color: colors.text,
  },
  metaLine: {
    ...fonts.caption,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  leaderRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
  },
  leaderRowPartner: {
    borderLeftWidth: 3,
    borderLeftColor: colors.accent,
    paddingLeft: spacing.md - 3,
  },
  leaderRowBordered: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: ROW_BORDER,
  },
  rankBlock: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    width: 76,
    paddingTop: 2,
  },
  rankText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
  },
  leaderMid: {
    flex: 1,
    marginRight: spacing.sm,
    minWidth: 0,
  },
  companyName: {
    ...fonts.regular,
    fontWeight: "500",
  },
  companyNamePartner: {
    fontWeight: "700",
    color: colors.accent,
  },
  locationText: {
    ...fonts.caption,
    marginTop: 2,
  },
  leaderRight: {
    alignItems: "flex-end",
    minWidth: 100,
  },
  revenueText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
  },
  avgCheckText: {
    ...fonts.caption,
    marginTop: 2,
  },
  changeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 4,
  },
  changeText: {
    fontSize: 12,
    fontWeight: "700",
  },
  separatorRow: {
    paddingVertical: spacing.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  separatorDots: {
    fontSize: 14,
    color: colors.textMuted,
    letterSpacing: 4,
  },
});
