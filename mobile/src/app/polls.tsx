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
} from "react-native";
import { Stack } from "expo-router";
import { Card } from "@/components/ui/Card";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import type { Poll } from "@/lib/types";

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
    <>
      <Stack.Screen options={{ headerTitle: "Опросы" }} />
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={refresh}
            tintColor={colors.gold}
          />
        }
      >
        {polls.length === 0 ? (
          <Card>
            <Text style={styles.emptyText}>Нет активных опросов</Text>
          </Card>
        ) : (
          polls.map((poll) => {
            const isVoted = voted.has(poll.id);
            const isVoting = voting === poll.id;
            const selectedOption = selected[poll.id];
            const sortedOptions = [...poll.options].sort(
              (a, b) => a.position - b.position,
            );

            return (
              <Card key={poll.id} style={styles.pollCard}>
                <Text style={styles.question}>{poll.question}</Text>

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
                          {isSelected && <View style={styles.radioDot} />}
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

                {isVoted ? (
                  <View style={styles.votedBadge}>
                    <Text style={styles.votedText}>✓ Голос учтён</Text>
                  </View>
                ) : (
                  <TouchableOpacity
                    style={[
                      styles.voteBtn,
                      (!selectedOption || isVoting) && styles.voteBtnDisabled,
                    ]}
                    disabled={!selectedOption || isVoting}
                    onPress={() => handleVote(poll)}
                  >
                    {isVoting ? (
                      <ActivityIndicator color={colors.bg} size="small" />
                    ) : (
                      <Text style={styles.voteBtnText}>Голосовать</Text>
                    )}
                  </TouchableOpacity>
                )}
              </Card>
            );
          })
        )}
      </ScrollView>
    </>
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
    paddingBottom: spacing.xl,
  },
  emptyText: {
    ...fonts.regular,
    color: colors.textMuted,
    textAlign: "center",
  },
  pollCard: {
    gap: spacing.md,
  },
  question: {
    ...fonts.medium,
    fontWeight: "700",
    lineHeight: 24,
  },
  options: {
    gap: spacing.sm,
  },
  option: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.sm,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  optionSelected: {
    borderColor: colors.gold,
    backgroundColor: `${colors.gold}15`,
  },
  optionDisabled: {
    opacity: 0.7,
  },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.textMuted,
    alignItems: "center",
    justifyContent: "center",
  },
  radioSelected: {
    borderColor: colors.gold,
  },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.gold,
  },
  optionText: {
    ...fonts.regular,
    flex: 1,
  },
  optionTextSelected: {
    color: colors.accentLight,
    fontWeight: "600",
  },
  voteBtn: {
    backgroundColor: colors.gold,
    borderRadius: radius.md,
    paddingVertical: 12,
    alignItems: "center",
  },
  voteBtnDisabled: {
    opacity: 0.4,
  },
  voteBtnText: {
    color: colors.bg,
    fontWeight: "800",
    fontSize: 15,
  },
  votedBadge: {
    backgroundColor: `${colors.success}20`,
    borderRadius: radius.sm,
    paddingVertical: spacing.sm,
    alignItems: "center",
  },
  votedText: {
    color: colors.success,
    fontWeight: "700",
    fontSize: 14,
  },
});
