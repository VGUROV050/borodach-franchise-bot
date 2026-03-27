import React, { useState } from "react";
import {
  ScrollView,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from "react-native";
import { Stack, useRouter } from "expo-router";
import { Card } from "@/components/ui/Card";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";
import type { Department, Company } from "@/lib/types";

type Step = "department" | "barbershop" | "title" | "description" | "confirm";

const STEPS: Step[] = [
  "department",
  "barbershop",
  "title",
  "description",
  "confirm",
];

const STEP_TITLES: Record<Step, string> = {
  department: "Выберите отдел",
  barbershop: "Выберите салон",
  title: "Заголовок задачи",
  description: "Описание задачи",
  confirm: "Подтверждение",
};

export default function CreateTaskScreen() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("department");
  const [selectedDept, setSelectedDept] = useState<Department | null>(null);
  const [selectedShop, setSelectedShop] = useState<Company | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const departments = useApi(() => api.getTaskDepartments());
  const companies = useApi(() => api.getCompanies());

  const stepIndex = STEPS.indexOf(step);

  function goNext() {
    if (stepIndex < STEPS.length - 1) setStep(STEPS[stepIndex + 1]);
  }

  function goBack() {
    if (stepIndex > 0) setStep(STEPS[stepIndex - 1]);
    else router.back();
  }

  async function handleSubmit() {
    if (!selectedDept || !selectedShop || !title.trim()) return;
    setSubmitting(true);
    try {
      await api.createTask({
        department_key: selectedDept.key,
        barbershop: selectedShop.name,
        title: title.trim(),
        description: description.trim(),
      });
      Alert.alert("Готово", "Задача создана", [
        { text: "OK", onPress: () => router.back() },
      ]);
    } catch {
      Alert.alert("Ошибка", "Не удалось создать задачу");
    } finally {
      setSubmitting(false);
    }
  }

  if (
    (departments.loading && !departments.data) ||
    (companies.loading && !companies.data)
  )
    return <LoadingScreen />;
  if (departments.error)
    return (
      <ErrorMessage
        message={departments.error}
        onRetry={departments.refresh}
      />
    );
  if (companies.error)
    return (
      <ErrorMessage message={companies.error} onRetry={companies.refresh} />
    );

  return (
    <>
      <Stack.Screen options={{ headerTitle: "Новая задача" }} />
      <View style={styles.screen}>
        <View style={styles.progress}>
          {STEPS.map((s, i) => (
            <View
              key={s}
              style={[styles.dot, i <= stepIndex && styles.dotActive]}
            />
          ))}
        </View>
        <Text style={styles.stepTitle}>{STEP_TITLES[step]}</Text>

        <ScrollView
          style={styles.scrollArea}
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          {step === "department" &&
            departments.data?.map((dept) => (
              <TouchableOpacity
                key={dept.key}
                activeOpacity={0.7}
                onPress={() => {
                  setSelectedDept(dept);
                  goNext();
                }}
              >
                <Card
                  style={[
                    styles.optionCard,
                    selectedDept?.key === dept.key && styles.optionSelected,
                  ]}
                >
                  <Text style={styles.optionText}>{dept.name}</Text>
                </Card>
              </TouchableOpacity>
            ))}

          {step === "barbershop" &&
            companies.data?.map((c) => (
              <TouchableOpacity
                key={c.id}
                activeOpacity={0.7}
                onPress={() => {
                  setSelectedShop(c);
                  goNext();
                }}
              >
                <Card
                  style={[
                    styles.optionCard,
                    selectedShop?.id === c.id && styles.optionSelected,
                  ]}
                >
                  <Text style={styles.optionText}>💈 {c.name}</Text>
                  {c.city && (
                    <Text style={styles.optionSub}>{c.city}</Text>
                  )}
                </Card>
              </TouchableOpacity>
            ))}

          {step === "title" && (
            <View style={styles.inputGroup}>
              <TextInput
                style={styles.input}
                placeholder="Введите заголовок"
                placeholderTextColor={colors.textMuted}
                value={title}
                onChangeText={setTitle}
                autoFocus
              />
              <TouchableOpacity
                style={[styles.nextBtn, !title.trim() && styles.btnDisabled]}
                disabled={!title.trim()}
                onPress={goNext}
              >
                <Text style={styles.nextBtnText}>Далее</Text>
              </TouchableOpacity>
            </View>
          )}

          {step === "description" && (
            <View style={styles.inputGroup}>
              <TextInput
                style={[styles.input, styles.textArea]}
                placeholder="Описание (необязательно)"
                placeholderTextColor={colors.textMuted}
                value={description}
                onChangeText={setDescription}
                multiline
                numberOfLines={4}
                textAlignVertical="top"
                autoFocus
              />
              <TouchableOpacity style={styles.nextBtn} onPress={goNext}>
                <Text style={styles.nextBtnText}>Далее</Text>
              </TouchableOpacity>
            </View>
          )}

          {step === "confirm" && (
            <View style={styles.confirmGroup}>
              <Card>
                <ConfirmRow label="Отдел" value={selectedDept?.name ?? ""} />
                <ConfirmRow label="Салон" value={selectedShop?.name ?? ""} />
                <ConfirmRow label="Заголовок" value={title} />
                {description.trim() !== "" && (
                  <ConfirmRow label="Описание" value={description} last />
                )}
              </Card>
              <TouchableOpacity
                style={[styles.submitBtn, submitting && styles.btnDisabled]}
                disabled={submitting}
                onPress={handleSubmit}
              >
                {submitting ? (
                  <ActivityIndicator color={colors.bg} />
                ) : (
                  <Text style={styles.submitBtnText}>Создать задачу</Text>
                )}
              </TouchableOpacity>
            </View>
          )}
        </ScrollView>

        {step !== "department" && (
          <TouchableOpacity style={styles.backBtn} onPress={goBack}>
            <Text style={styles.backBtnText}>← Назад</Text>
          </TouchableOpacity>
        )}
      </View>
    </>
  );
}

function ConfirmRow({
  label,
  value,
  last,
}: {
  label: string;
  value: string;
  last?: boolean;
}) {
  return (
    <View style={[styles.confirmRow, !last && styles.confirmRowBorder]}>
      <Text style={styles.confirmLabel}>{label}</Text>
      <Text style={styles.confirmValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  progress: {
    flexDirection: "row",
    justifyContent: "center",
    gap: spacing.sm,
    paddingVertical: spacing.md,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.border,
  },
  dotActive: {
    backgroundColor: colors.gold,
  },
  stepTitle: {
    ...fonts.large,
    textAlign: "center",
    marginBottom: spacing.md,
  },
  scrollArea: {
    flex: 1,
  },
  content: {
    padding: spacing.md,
    gap: spacing.sm,
    paddingBottom: spacing.xl,
  },
  optionCard: {
    gap: spacing.xs,
  },
  optionSelected: {
    borderColor: colors.gold,
    borderWidth: 1.5,
  },
  optionText: {
    ...fonts.medium,
    fontWeight: "600",
  },
  optionSub: {
    ...fonts.caption,
  },
  inputGroup: {
    gap: spacing.md,
  },
  input: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    color: colors.text,
    fontSize: 16,
  },
  textArea: {
    minHeight: 120,
  },
  nextBtn: {
    backgroundColor: colors.gold,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: "center",
  },
  nextBtnText: {
    color: colors.bg,
    fontWeight: "800",
    fontSize: 16,
  },
  btnDisabled: {
    opacity: 0.5,
  },
  confirmGroup: {
    gap: spacing.lg,
  },
  confirmRow: {
    paddingVertical: spacing.sm,
  },
  confirmRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  confirmLabel: {
    ...fonts.caption,
    marginBottom: 2,
  },
  confirmValue: {
    ...fonts.regular,
    fontWeight: "600",
  },
  submitBtn: {
    backgroundColor: colors.gold,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: "center",
  },
  submitBtnText: {
    color: colors.bg,
    fontWeight: "800",
    fontSize: 16,
  },
  backBtn: {
    padding: spacing.md,
    alignItems: "center",
  },
  backBtnText: {
    ...fonts.regular,
    color: colors.textSecondary,
    fontWeight: "600",
  },
});
