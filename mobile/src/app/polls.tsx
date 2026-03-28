import React, { useState } from "react";
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
  ActivityIndicator,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { ClipboardList, Check } from "lucide-react-native";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import { formatDate } from "@/lib/formatters";
import type { Poll } from "@/lib/types";

const HEADER_ICON = 32;
const ACCENT = "#5CAE5D";
const OPTION_BG = "#F8F8FA";

export default function PollsScreen() {
  const { data, loading, error, refresh } = useApi(() => api.getPolls());
  const [selected, setSelected] = useState<Record<number, number>>({});
  const [voting, setVoting] = useState<number | null>(null);
  const [voted, setVoted] = useState<Set<number>>(new Set());

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorMessage message={error} onRetry={refresh} />;

  const polls = data ?? [];

  async function handleVote(poll: Poll) {
    const optionId = selected[poll.id];
    if (!optionId) return;
    setVoting(poll.id);
    try {
      await api.votePoll(poll.id, [optionId]);
      setVoted((prev) => new Set(prev).add(poll.id));
    } catch {
      Alert.alert("Ошибка", "Не удалось проголосовать");
    } finally {
      setVoting(null);
    }
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.header}>
        <ClipboardList size={HEADER_ICON} color={ACCENT} strokeWidth={2} />
        <Text style={styles.headerTitle}>Опросы</Text>
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
        {polls.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyText}>Нет активных опросов</Text>
          </View>
        ) : (
          polls.map((poll) => {
            const isVoted = voted.has(poll.id);
            const isVoting = voting === poll.id;
            const selectedOption = selected[poll.id];
            const sortedOptions = [...poll.options].sort(
              (a, b) => a.position - b.position,
            );

            return (
              <View key={poll.id} style={styles.pollCard}>
                <Text style={styles.question}>{poll.question}</Text>
                <Text style={styles.dateMuted}>
                  {formatDate(poll.created_at)}
                </Text>

                {isVoted ? (
                  <View style={styles.votedBadge}>
                    <Check size={18} color={ACCENT} strokeWidth={2.5} />
                    <Text style={styles.votedText}>Вы проголосовали</Text>
                  </View>
                ) : null}

                <View style={styles.options}>
                  {sortedOptions.map((opt) => {
                    const isSelected = selectedOption === opt.id;
                    return (
                      <TouchableOpacity
                        key={opt.id}
                        style={[
                          styles.option,
                          isSelected && styles.optionSelected,
                          isVoted && styles.optionDisabled,
                        ]}
                        activeOpacity={0.7}
                        disabled={isVoted}
                        onPress={() =>
                          setSelected((prev) => ({
                            ...prev,
                            [poll.id]: opt.id,
                          }))
                        }
                      >
                        <View
                          style={[
                            styles.radio,
                            isSelected && styles.radioSelected,
                          ]}
                        >
                          {isSelected ? (
                            <View style={styles.radioDot} />
                          ) : null}
                        </View>
                        <Text
                          style={[
                            styles.optionText,
                            isSelected && styles.optionTextSelected,
                          ]}
                        >
                          {opt.text}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>

                {!isVoted && selectedOption ? (
                  <TouchableOpacity
                    style={[
                      styles.voteBtn,
                      isVoting && styles.voteBtnDisabled,
                    ]}
                    disabled={isVoting}
                    onPress={() => handleVote(poll)}
                  >
                    {isVoting ? (
                      <ActivityIndicator color={colors.white} size="small" />
                    ) : (
                      <Text style={styles.voteBtnText}>Голосовать</Text>
                    )}
                  </TouchableOpacity>
                ) : null}
              </View>
            );
          })
        )}
      </ScrollView>
    </SafeAreaView>
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
  emptyCard: {
    backgroundColor: colors.white,
    borderRadius: radius.md,
    padding: spacing.lg,
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 6,
      },
      android: { elevation: 3 },
      default: {},
    }),
  },
  emptyText: {
    ...fonts.regular,
    color: colors.textMuted,
    textAlign: "center",
  },
  pollCard: {
    backgroundColor: colors.white,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: spacing.sm,
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 6,
      },
      android: { elevation: 3 },
      default: {},
    }),
  },
  question: {
    fontSize: 17,
    fontWeight: "600",
    color: colors.text,
    lineHeight: 24,
  },
  dateMuted: {
    ...fonts.caption,
    color: colors.textMuted,
    marginTop: -spacing.xs,
  },
  options: {
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  option: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.sm,
    borderRadius: radius.sm,
    borderWidth: 2,
    borderColor: "transparent",
    backgroundColor: OPTION_BG,
  },
  optionSelected: {
    borderColor: ACCENT,
    backgroundColor: OPTION_BG,
  },
  optionDisabled: {
    opacity: 0.7,
  },
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: colors.textMuted,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "transparent",
  },
  radioSelected: {
    borderColor: ACCENT,
    backgroundColor: ACCENT,
  },
  radioDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.white,
  },
  optionText: {
    ...fonts.regular,
    flex: 1,
    color: colors.text,
  },
  optionTextSelected: {
    fontWeight: "600",
  },
  voteBtn: {
    backgroundColor: ACCENT,
    borderRadius: radius.md,
    paddingVertical: 12,
    alignItems: "center",
    marginTop: spacing.sm,
  },
  voteBtnDisabled: {
    opacity: 0.7,
  },
  voteBtnText: {
    color: colors.white,
    fontWeight: "700",
    fontSize: 16,
  },
  votedBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    alignSelf: "flex-start",
    backgroundColor: "rgba(92,174,93,0.12)",
    borderRadius: radius.sm,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
  },
  votedText: {
    color: ACCENT,
    fontWeight: "600",
    fontSize: 14,
  },
});
