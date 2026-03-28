import React, { useState } from "react";
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { BookOpen, ChevronDown, ChevronUp } from "lucide-react-native";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import type { DepartmentButton } from "@/lib/types";

const HEADER_ICON = 32;
const ACCENT = "#5CAE5D";

export default function UsefulScreen() {
  const { data, loading, error, refresh } = useApi(() => api.getDepartments());
  const [expanded, setExpanded] = useState<string | null>(null);
  const [expandedBtn, setExpandedBtn] = useState<number | null>(null);
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
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.header}>
        <BookOpen size={HEADER_ICON} color={ACCENT} strokeWidth={2} />
        <Text style={styles.headerTitle}>Полезное</Text>
      </View>
      <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
        {data?.map((dept) => {
          const isOpen = expanded === dept.key;
          return (
            <View key={dept.key} style={styles.deptGroup}>
              <TouchableOpacity
                activeOpacity={0.7}
                onPress={() => toggleDepartment(dept.key)}
                style={[styles.deptCard, isOpen && styles.deptCardActive]}
              >
                <Text style={[styles.deptName, isOpen && styles.deptNameActive]}>
                  {dept.name}
                </Text>
                {isOpen ? (
                  <ChevronUp size={20} color={colors.accent} />
                ) : (
                  <ChevronDown size={20} color={colors.textMuted} />
                )}
              </TouchableOpacity>

              {isOpen && (
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
                      <View key={btn.id}>
                        <TouchableOpacity
                          style={[
                            styles.btnCard,
                            expandedBtn === btn.id && styles.btnCardActive,
                          ]}
                          activeOpacity={0.7}
                          onPress={() =>
                            setExpandedBtn(expandedBtn === btn.id ? null : btn.id)
                          }
                        >
                          <Text
                            style={[
                              styles.btnTitle,
                              expandedBtn === btn.id && styles.btnTitleActive,
                            ]}
                          >
                            {btn.button_text}
                          </Text>
                          {expandedBtn === btn.id ? (
                            <ChevronUp size={18} color={colors.accent} />
                          ) : (
                            <ChevronDown size={18} color={colors.textMuted} />
                          )}
                        </TouchableOpacity>
                        {expandedBtn === btn.id && (
                          <View style={styles.btnContent}>
                            <Text style={styles.btnMessage}>
                              {btn.message_text}
                            </Text>
                          </View>
                        )}
                      </View>
                    ))
                  )}
                </View>
              )}
            </View>
          );
        })}
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
    gap: spacing.sm,
    paddingBottom: 100,
  },
  deptGroup: {
    gap: spacing.sm,
  },
  deptCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: "transparent",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  deptCardActive: {
    borderColor: colors.accent,
    backgroundColor: colors.accentLight,
  },
  deptName: {
    ...fonts.medium,
    fontWeight: "600",
    flex: 1,
    color: colors.text,
  },
  deptNameActive: {
    color: colors.accent,
  },
  buttonsList: {
    gap: spacing.sm,
    paddingLeft: spacing.sm,
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
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: spacing.md,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
    elevation: 1,
  },
  btnCardActive: {
    borderBottomLeftRadius: 0,
    borderBottomRightRadius: 0,
  },
  btnTitle: {
    ...fonts.regular,
    fontWeight: "600",
    color: colors.text,
    flex: 1,
    marginRight: spacing.sm,
  },
  btnTitleActive: {
    color: colors.accent,
  },
  btnContent: {
    backgroundColor: colors.card,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    borderBottomLeftRadius: radius.md,
    borderBottomRightRadius: radius.md,
    padding: spacing.md,
  },
  btnMessage: {
    ...fonts.regular,
    color: colors.textSecondary,
    lineHeight: 20,
  },
});
