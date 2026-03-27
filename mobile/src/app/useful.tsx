import React, { useState } from "react";
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { Stack } from "expo-router";
import { Card } from "@/components/ui/Card";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import type { DepartmentButton } from "@/lib/types";

export default function UsefulScreen() {
  const { data, loading, error, refresh } = useApi(() => api.getDepartments());
  const [expanded, setExpanded] = useState<string | null>(null);
  const [buttons, setButtons] = useState<Record<string, DepartmentButton[]>>(
    {},
  );
  const [loadingDept, setLoadingDept] = useState<string | null>(null);

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorMessage message={error} onRetry={refresh} />;

  async function toggleDepartment(key: string) {
    if (expanded === key) {
      setExpanded(null);
      return;
    }
    setExpanded(key);
    if (!buttons[key]) {
      setLoadingDept(key);
      try {
        const result = await api.getDepartmentButtons(key);
        setButtons((prev) => ({ ...prev, [key]: result }));
      } catch {
        setButtons((prev) => ({ ...prev, [key]: [] }));
      } finally {
        setLoadingDept(null);
      }
    }
  }

  return (
    <>
      <Stack.Screen options={{ headerTitle: "Полезное" }} />
      <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
        {data?.map((dept) => (
          <View key={dept.key}>
            <TouchableOpacity
              activeOpacity={0.7}
              onPress={() => toggleDepartment(dept.key)}
            >
              <Card
                style={[
                  styles.deptCard,
                  expanded === dept.key && styles.deptCardExpanded,
                ]}
              >
                <Text style={styles.deptName}>{dept.name}</Text>
                <Text style={styles.chevron}>
                  {expanded === dept.key ? "▾" : "›"}
                </Text>
              </Card>
            </TouchableOpacity>

            {expanded === dept.key && (
              <View style={styles.buttonsList}>
                {loadingDept === dept.key ? (
                  <ActivityIndicator
                    color={colors.accent}
                    style={styles.loader}
                  />
                ) : buttons[dept.key]?.length === 0 ? (
                  <Text style={styles.emptyText}>Нет информации</Text>
                ) : (
                  buttons[dept.key]?.map((btn) => (
                    <Card key={btn.id} style={styles.btnCard}>
                      <Text style={styles.btnTitle}>{btn.button_text}</Text>
                      <Text style={styles.btnMessage}>
                        {btn.message_text}
                      </Text>
                    </Card>
                  ))
                )}
              </View>
            )}
          </View>
        ))}
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
    gap: spacing.sm,
    paddingBottom: 100,
  },
  deptCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  deptCardExpanded: {
    borderColor: colors.accent,
    borderWidth: 1.5,
    borderBottomLeftRadius: 0,
    borderBottomRightRadius: 0,
  },
  deptName: {
    ...fonts.medium,
    fontWeight: "600",
  },
  chevron: {
    fontSize: 18,
    color: colors.textMuted,
  },
  buttonsList: {
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderTopWidth: 0,
    borderColor: colors.border,
    borderBottomLeftRadius: radius.md,
    borderBottomRightRadius: radius.md,
    padding: spacing.sm,
    gap: spacing.sm,
  },
  loader: {
    padding: spacing.md,
  },
  emptyText: {
    ...fonts.regular,
    color: colors.textMuted,
    textAlign: "center",
    padding: spacing.md,
  },
  btnCard: {
    backgroundColor: colors.cardAlt,
    gap: spacing.xs,
  },
  btnTitle: {
    ...fonts.regular,
    fontWeight: "700",
    color: colors.accentLight,
  },
  btnMessage: {
    ...fonts.regular,
    color: colors.textSecondary,
    lineHeight: 20,
  },
});
