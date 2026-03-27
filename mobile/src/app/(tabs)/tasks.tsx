import React, { useState } from "react";
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import { Card } from "@/components/ui/Card";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import { formatDate } from "@/lib/formatters";
import type { Task } from "@/lib/types";

export default function TasksScreen() {
  const [activeOnly, setActiveOnly] = useState(true);
  const { data, loading, error, refresh } = useApi(
    () => api.getTasks(activeOnly),
    [activeOnly],
  );
  const router = useRouter();

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorMessage message={error} onRetry={refresh} />;

  const tasks = data ?? [];
  const grouped = groupTasks(tasks);

  async function handleCancel(taskId: number) {
    Alert.alert("Отменить задачу", `Отменить задачу #${taskId}?`, [
      { text: "Нет", style: "cancel" },
      {
        text: "Да, отменить",
        style: "destructive",
        onPress: async () => {
          try {
            await api.cancelTask(taskId);
            refresh();
          } catch {
            Alert.alert("Ошибка", "Не удалось отменить задачу");
          }
        },
      },
    ]);
  }

  return (
    <View style={styles.screen}>
      <View style={styles.toggle}>
        <TouchableOpacity
          style={[styles.toggleBtn, activeOnly && styles.toggleBtnActive]}
          onPress={() => setActiveOnly(true)}
        >
          <Text
            style={[
              styles.toggleText,
              activeOnly && styles.toggleTextActive,
            ]}
          >
            В работе
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleBtn, !activeOnly && styles.toggleBtnActive]}
          onPress={() => setActiveOnly(false)}
        >
          <Text
            style={[
              styles.toggleText,
              !activeOnly && styles.toggleTextActive,
            ]}
          >
            Все задачи
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={refresh}
            tintColor={colors.gold}
          />
        }
      >
        {tasks.length === 0 ? (
          <Card>
            <Text style={styles.emptyText}>Нет задач</Text>
          </Card>
        ) : (
          Object.entries(grouped).map(([shop, departments]) => (
            <View key={shop} style={styles.group}>
              <Text style={styles.groupTitle}>💈 {shop}</Text>
              {Object.entries(departments).map(([dept, stages]) => (
                <View key={dept} style={styles.subgroup}>
                  <Text style={styles.subgroupTitle}>{dept}</Text>
                  {Object.entries(stages).map(([stage, items]) => (
                    <View key={stage}>
                      <Text style={styles.stageLabel}>{stage}</Text>
                      {items.map((task) => (
                        <Card key={task.id} style={styles.taskCard}>
                          <View style={styles.taskHeader}>
                            <Text style={styles.taskEmoji}>
                              {task.stage_emoji}
                            </Text>
                            <Text style={styles.taskId}>#{task.id}</Text>
                            <Text style={styles.taskDate}>
                              {formatDate(task.created_at)}
                            </Text>
                          </View>
                          <Text style={styles.taskTitle}>
                            {task.title}
                          </Text>
                          {activeOnly && (
                            <TouchableOpacity
                              style={styles.cancelBtn}
                              onPress={() => handleCancel(task.id)}
                            >
                              <Text style={styles.cancelText}>Отменить</Text>
                            </TouchableOpacity>
                          )}
                        </Card>
                      ))}
                    </View>
                  ))}
                </View>
              ))}
            </View>
          ))
        )}
      </ScrollView>

      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push("/create-task")}
        activeOpacity={0.8}
      >
        <Text style={styles.fabText}>＋ Новая задача</Text>
      </TouchableOpacity>
    </View>
  );
}

type GroupedTasks = Record<string, Record<string, Record<string, Task[]>>>;

function groupTasks(tasks: Task[]): GroupedTasks {
  const result: GroupedTasks = {};
  for (const t of tasks) {
    const shop = t.barbershop ?? "Не указан";
    if (!result[shop]) result[shop] = {};
    if (!result[shop][t.department_name])
      result[shop][t.department_name] = {};
    const stageKey = `${t.stage_emoji} ${t.stage}`;
    if (!result[shop][t.department_name][stageKey])
      result[shop][t.department_name][stageKey] = [];
    result[shop][t.department_name][stageKey].push(t);
  }
  return result;
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  toggle: {
    flexDirection: "row",
    margin: spacing.md,
    backgroundColor: colors.card,
    borderRadius: radius.sm,
    padding: 2,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: spacing.sm,
    alignItems: "center",
    borderRadius: radius.sm - 2,
  },
  toggleBtnActive: {
    backgroundColor: colors.gold,
  },
  toggleText: {
    ...fonts.regular,
    fontWeight: "600",
    color: colors.textMuted,
  },
  toggleTextActive: {
    color: colors.bg,
  },
  content: {
    padding: spacing.md,
    paddingTop: 0,
    gap: spacing.md,
    paddingBottom: 100,
  },
  emptyText: {
    ...fonts.regular,
    color: colors.textMuted,
    textAlign: "center",
  },
  group: {
    gap: spacing.sm,
  },
  groupTitle: {
    ...fonts.large,
  },
  subgroup: {
    gap: spacing.xs,
    marginLeft: spacing.sm,
  },
  subgroupTitle: {
    ...fonts.medium,
    color: colors.accentLight,
    fontWeight: "600",
  },
  stageLabel: {
    ...fonts.caption,
    marginTop: spacing.xs,
    marginBottom: spacing.xs,
  },
  taskCard: {
    gap: spacing.xs,
  },
  taskHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  taskEmoji: {
    fontSize: 16,
  },
  taskId: {
    ...fonts.caption,
    color: colors.gold,
    fontWeight: "700",
  },
  taskDate: {
    ...fonts.caption,
    marginLeft: "auto",
  },
  taskTitle: {
    ...fonts.regular,
  },
  cancelBtn: {
    alignSelf: "flex-start",
    marginTop: spacing.xs,
  },
  cancelText: {
    ...fonts.caption,
    color: colors.danger,
    fontWeight: "600",
  },
  fab: {
    position: "absolute",
    bottom: 24,
    right: spacing.md,
    left: spacing.md,
    backgroundColor: colors.gold,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: "center",
    shadowColor: colors.gold,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  fabText: {
    color: colors.bg,
    fontWeight: "800",
    fontSize: 16,
  },
});
