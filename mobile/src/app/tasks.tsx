import React, { useState, useCallback } from "react";
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
  Modal,
  Pressable,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useFocusEffect } from "expo-router";
import { CheckSquare, Plus, X } from "lucide-react-native";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import { formatDate } from "@/lib/formatters";
import type { Task } from "@/lib/types";

const INFO_CARD_BG = "#F8F8FA";

export default function TasksScreen() {
  const [activeOnly, setActiveOnly] = useState(true);
  const { data, loading, error, refresh } = useApi(
    () => api.getTasks(activeOnly),
    [activeOnly],
  );
  const router = useRouter();

  useFocusEffect(
    useCallback(() => {
      refresh();
    }, [activeOnly])
  );

  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [cancelTaskId, setCancelTaskId] = useState<number | null>(null);
  const [cancelSubmitting, setCancelSubmitting] = useState(false);

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorMessage message={error} onRetry={refresh} />;

  const tasks = data ?? [];
  const grouped = groupTasks(tasks);

  function openCancelFlow(taskId: number) {
    setCancelTaskId(taskId);
  }

  function closeCancelConfirm() {
    if (!cancelSubmitting) setCancelTaskId(null);
  }

  async function confirmCancel() {
    if (cancelTaskId == null) return;
    setCancelSubmitting(true);
    try {
      await api.cancelTask(cancelTaskId);
      setCancelTaskId(null);
      setSelectedTask(null);
      refresh();
    } catch {
      Alert.alert("Ошибка", "Не удалось отменить задачу");
    } finally {
      setCancelSubmitting(false);
    }
  }

  function stageLabel(task: Task) {
    return task.stage ?? "";
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.screen}>
        <View style={styles.header}>
          <CheckSquare size={32} color={colors.accent} strokeWidth={2} />
          <Text style={styles.headerTitle}>Задачи</Text>
        </View>

        <View style={styles.filterRow}>
          <View style={styles.chips}>
            <TouchableOpacity
              style={[styles.chip, activeOnly && styles.chipActive]}
              onPress={() => setActiveOnly(true)}
              activeOpacity={0.85}
            >
              <Text
                style={[styles.chipText, activeOnly && styles.chipTextActive]}
              >
                Активные
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.chip, !activeOnly && styles.chipActive]}
              onPress={() => setActiveOnly(false)}
              activeOpacity={0.85}
            >
              <Text
                style={[styles.chipText, !activeOnly && styles.chipTextActive]}
              >
                Все
              </Text>
            </TouchableOpacity>
          </View>
          <TouchableOpacity
            style={styles.addButton}
            onPress={() => router.push("/create-task")}
            activeOpacity={0.85}
            accessibilityRole="button"
            accessibilityLabel="Новая задача"
          >
            <Plus size={20} color={colors.white} strokeWidth={2.5} />
          </TouchableOpacity>
        </View>

        <ScrollView
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={loading}
              onRefresh={refresh}
              tintColor={colors.accent}
            />
          }
        >
          {tasks.length === 0 ? (
            <View style={styles.emptyWrap}>
              <Text style={styles.emptyText}>Нет задач</Text>
            </View>
          ) : (
            Object.entries(grouped).map(([shop, departments]) => (
              <View key={shop} style={styles.group}>
                <Text style={styles.shopTitle}>{shop}</Text>
                {Object.entries(departments).map(([dept, stages]) =>
                  Object.entries(stages).map(([stageKey, items]) => (
                    <View key={`${dept}-${stageKey}`} style={styles.subgroup}>
                      <Text style={styles.deptStage}>
                        {dept} • {stageKey}
                      </Text>
                      <View style={styles.taskList}>
                        {items.map((task) => (
                          <View key={task.id} style={styles.taskCard}>
                            <Pressable
                              style={styles.taskCardPress}
                              onPress={() => setSelectedTask(task)}
                              accessibilityRole="button"
                            >
                              <View style={styles.taskCardBody}>
                                <Text style={styles.taskTitle} numberOfLines={3}>
                                  {task.title}
                                </Text>
                                <Text style={styles.taskDate}>
                                  Создана {formatDate(task.created_at)}
                                </Text>
                              </View>
                            </Pressable>
                            {activeOnly ? (
                              <TouchableOpacity
                                style={styles.taskCancelIcon}
                                onPress={() => openCancelFlow(task.id)}
                                hitSlop={8}
                                accessibilityRole="button"
                                accessibilityLabel="Отменить задачу"
                              >
                                <X size={16} color={colors.textSecondary} />
                              </TouchableOpacity>
                            ) : null}
                          </View>
                        ))}
                      </View>
                    </View>
                  )),
                )}
              </View>
            ))
          )}
        </ScrollView>
      </View>

      <Modal
        visible={selectedTask !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setSelectedTask(null)}
      >
        {selectedTask ? (
          <View style={styles.modalRoot}>
            <Pressable
              style={styles.modalBackdrop}
              onPress={() => setSelectedTask(null)}
              accessibilityRole="button"
              accessibilityLabel="Закрыть"
            />
            <View style={styles.detailSheet}>
              <View style={styles.detailHeaderRow}>
                <Text style={styles.detailTitle} numberOfLines={4}>
                  {selectedTask.title}
                </Text>
                <TouchableOpacity
                  style={styles.detailCloseBtn}
                  onPress={() => setSelectedTask(null)}
                  hitSlop={8}
                >
                  <X size={18} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              <ScrollView
                style={styles.detailScroll}
                showsVerticalScrollIndicator={false}
                keyboardShouldPersistTaps="handled"
              >
                <InfoRow label="Барбершоп" value={selectedTask.barbershop ?? "—"} />
                <InfoRow label="Отдел" value={selectedTask.department_name} />
                <InfoRow label="Стадия" value={stageLabel(selectedTask)} />
                <InfoRow
                  label="Статус"
                  value={activeOnly ? "В работе" : "—"}
                />
                <InfoRow
                  label="Дата создания"
                  value={formatDate(selectedTask.created_at)}
                />
                <View style={styles.infoCard}>
                  <Text style={styles.infoLabel}>Описание</Text>
                  <Text style={styles.infoDescription}>—</Text>
                </View>
              </ScrollView>

              <View style={styles.detailActions}>
                {activeOnly ? (
                  <TouchableOpacity
                    style={styles.btnCancelTask}
                    onPress={() => openCancelFlow(selectedTask.id)}
                    activeOpacity={0.85}
                  >
                    <Text style={styles.btnCancelTaskText}>Отменить задачу</Text>
                  </TouchableOpacity>
                ) : null}
                <TouchableOpacity
                  style={styles.btnCloseGreen}
                  onPress={() => setSelectedTask(null)}
                  activeOpacity={0.85}
                >
                  <Text style={styles.btnCloseGreenText}>Закрыть</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        ) : null}
      </Modal>

      <Modal
        visible={cancelTaskId !== null}
        transparent
        animationType="fade"
        onRequestClose={closeCancelConfirm}
      >
        <View style={styles.modalRoot}>
          <Pressable
            style={styles.modalBackdrop}
            onPress={closeCancelConfirm}
            accessibilityRole="button"
          />
          <View style={styles.confirmSheet}>
            <Text style={styles.confirmTitle}>Отмена задачи</Text>
            <Text style={styles.confirmMessage}>
              Вы уверены что хотите отменить задачу?
            </Text>
            <View style={styles.confirmActions}>
              <TouchableOpacity
                style={styles.btnGray}
                onPress={closeCancelConfirm}
                disabled={cancelSubmitting}
                activeOpacity={0.85}
              >
                <Text style={styles.btnGrayText}>Отмена</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.btnGreen}
                onPress={confirmCancel}
                disabled={cancelSubmitting}
                activeOpacity={0.85}
              >
                {cancelSubmitting ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <Text style={styles.btnGreenText}>Подтвердить</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoCard}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
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
    const stageKey = t.stage ?? "";
    if (!result[shop][t.department_name][stageKey])
      result[shop][t.department_name][stageKey] = [];
    result[shop][t.department_name][stageKey].push(t);
  }
  return result;
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  screen: {
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
  filterRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.md,
    gap: spacing.sm,
  },
  chips: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    flex: 1,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 999,
    backgroundColor: colors.cardAlt,
    borderWidth: 1,
    borderColor: "transparent",
  },
  chipActive: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  chipText: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  chipTextActive: {
    color: colors.accent,
  },
  addButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.accent,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 4,
  },
  content: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.xl,
    gap: spacing.md,
  },
  emptyWrap: {
    paddingVertical: spacing.xl,
  },
  emptyText: {
    ...fonts.regular,
    color: colors.textMuted,
    textAlign: "center",
  },
  group: {
    gap: spacing.sm,
  },
  shopTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
    marginBottom: spacing.xs,
  },
  subgroup: {
    marginBottom: spacing.sm,
  },
  deptStage: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  taskList: {
    gap: spacing.sm,
  },
  taskCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: colors.card,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    paddingLeft: spacing.md,
    paddingRight: spacing.sm,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  taskCardPress: {
    flex: 1,
    minWidth: 0,
  },
  taskCardBody: {
    gap: 4,
    paddingRight: spacing.xs,
  },
  taskTitle: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.text,
  },
  taskDate: {
    fontSize: 13,
    fontWeight: "400",
    color: colors.textSecondary,
  },
  taskCancelIcon: {
    paddingTop: 2,
    paddingLeft: spacing.xs,
  },
  modalRoot: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: spacing.md,
  },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.5)",
  },
  detailSheet: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    maxHeight: "80%",
    padding: spacing.lg,
    zIndex: 1,
  },
  detailHeaderRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  detailTitle: {
    flex: 1,
    fontSize: 22,
    fontWeight: "700",
    color: colors.text,
  },
  detailCloseBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: INFO_CARD_BG,
    alignItems: "center",
    justifyContent: "center",
  },
  detailScroll: {
    maxHeight: 360,
  },
  infoCard: {
    backgroundColor: INFO_CARD_BG,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  infoLabel: {
    fontSize: 13,
    fontWeight: "400",
    color: colors.textSecondary,
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.text,
  },
  infoDescription: {
    fontSize: 15,
    fontWeight: "400",
    color: colors.text,
    lineHeight: 22,
  },
  detailActions: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  btnCancelTask: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: radius.md,
    backgroundColor: INFO_CARD_BG,
    alignItems: "center",
    justifyContent: "center",
  },
  btnCancelTaskText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.danger,
  },
  btnCloseGreen: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: radius.md,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  btnCloseGreenText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.white,
  },
  confirmSheet: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.lg,
    zIndex: 1,
  },
  confirmTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.text,
    marginBottom: spacing.md,
  },
  confirmMessage: {
    fontSize: 15,
    fontWeight: "400",
    color: colors.textSecondary,
    marginBottom: spacing.lg,
  },
  confirmActions: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  btnGray: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: radius.md,
    backgroundColor: INFO_CARD_BG,
    alignItems: "center",
    justifyContent: "center",
  },
  btnGrayText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  btnGreen: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: radius.md,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 48,
  },
  btnGreenText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.white,
  },
});
