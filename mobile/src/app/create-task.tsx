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
  Pressable,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";
import { ArrowLeft } from "lucide-react-native";
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
  const insets = useSafeAreaInsets();
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
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.overlay}>
        <Pressable style={styles.backdrop} onPress={() => router.back()} />
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={styles.sheetWrap}
        >
          <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.md }]}>
            <View style={styles.dragHandle} />
            <View style={styles.topBar}>
              {stepIndex > 0 ? (
                <TouchableOpacity
                  style={styles.backArrow}
                  onPress={goBack}
                  activeOpacity={0.7}
                  hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
                >
                  <ArrowLeft size={20} color={colors.text} strokeWidth={2} />
                </TouchableOpacity>
              ) : (
                <View style={styles.backArrow} />
              )}
              <Text style={styles.topBarTitle}>Новая задача</Text>
              <TouchableOpacity
                onPress={() => router.back()}
                activeOpacity={0.7}
                hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
              >
                <Text style={styles.cancelText}>Отмена</Text>
              </TouchableOpacity>
            </View>
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
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <Text style={styles.submitBtnText}>Создать задачу</Text>
                )}
              </TouchableOpacity>
            </View>
          )}
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
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
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  sheetWrap: {
    maxHeight: "80%",
  },
  sheet: {
    backgroundColor: colors.card,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
  },
  dragHandle: {
    alignSelf: "center",
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.border,
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
  },
  backArrow: {
    width: 32,
  },
  cancelText: {
    fontSize: 15,
    color: colors.danger,
    fontWeight: "500",
  },
  topBarTitle: {
    flex: 1,
    textAlign: "center",
    fontSize: 17,
    fontWeight: "600",
    color: colors.text,
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
    backgroundColor: colors.accent,
  },
  stepTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.textSecondary,
    textAlign: "center",
    marginBottom: spacing.sm,
  },
  scrollArea: {
    flexGrow: 0,
  },
  content: {
    padding: spacing.md,
    gap: spacing.sm,
  },
  optionCard: {
    gap: spacing.xs,
  },
  optionSelected: {
    borderColor: colors.accent,
    borderWidth: 0.5,
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
    borderWidth: 0.5,
    borderColor: colors.border,
    padding: spacing.md,
    color: colors.text,
    fontSize: 16,
  },
  textArea: {
    minHeight: 120,
  },
  nextBtn: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: "center",
  },
  nextBtnText: {
    color: colors.white,
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
    borderBottomWidth: 0.5,
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
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: "center",
  },
  submitBtnText: {
    color: colors.white,
    fontWeight: "800",
    fontSize: 16,
  },
});
