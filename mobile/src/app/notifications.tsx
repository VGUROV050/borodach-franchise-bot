import React, { useMemo, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Modal,
  Pressable,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";
import {
  ArrowLeft,
  AlertTriangle,
  Info,
  BarChart3,
  Trophy,
  Bell,
  Check,
} from "lucide-react-native";
import { colors, spacing, radius } from "@/lib/theme";

type NotificationIcon = "alert" | "info" | "chart" | "trophy";
type NotificationType = "warning" | "info";

type NotificationItem = {
  id: number;
  type: NotificationType;
  icon: NotificationIcon;
  title: string;
  text: string;
  time: string;
  date: string;
  isRead: boolean;
};

const mockNotifications: NotificationItem[] = [
  {
    id: 1,
    type: "warning",
    icon: "alert",
    title: "Требуется внимание",
    text: "У вас 3 непроверенные задачи",
    time: "10:30",
    date: "Сегодня",
    isRead: false,
  },
  {
    id: 2,
    type: "info",
    icon: "info",
    title: "Новое обновление",
    text: "Доступна новая версия системы отчетности",
    time: "09:15",
    date: "Сегодня",
    isRead: false,
  },
  {
    id: 3,
    type: "info",
    icon: "info",
    title: "Новый опрос",
    text: "Пройдите опрос о качестве работы офиса",
    time: "08:45",
    date: "Сегодня",
    isRead: true,
  },
  {
    id: 4,
    type: "info",
    icon: "chart",
    title: "Статистика готова",
    text: "Отчет за февраль доступен для просмотра",
    time: "18:20",
    date: "Вчера",
    isRead: true,
  },
  {
    id: 5,
    type: "info",
    icon: "trophy",
    title: "Поздравляем!",
    text: "Ваш салон занял 1 место в рейтинге",
    time: "12:30",
    date: "Вчера",
    isRead: true,
  },
];

const DATE_ORDER = ["Сегодня", "Вчера"];

function groupByDate(items: NotificationItem[]) {
  const map = new Map<string, NotificationItem[]>();
  for (const n of items) {
    const list = map.get(n.date) ?? [];
    list.push(n);
    map.set(n.date, list);
  }
  return DATE_ORDER.filter((d) => (map.get(d)?.length ?? 0) > 0).map(
    (d) => [d, map.get(d)!] as const,
  );
}

function CardIcon({
  icon,
  color,
  size,
}: {
  icon: NotificationIcon;
  color: string;
  size: number;
}) {
  switch (icon) {
    case "alert":
      return <AlertTriangle size={size} color={color} />;
    case "info":
      return <Info size={size} color={color} />;
    case "chart":
      return <BarChart3 size={size} color={color} />;
    case "trophy":
      return <Trophy size={size} color={color} />;
    default:
      return <Info size={size} color={color} />;
  }
}

export default function NotificationsScreen() {
  const router = useRouter();
  const [notifications, setNotifications] =
    useState<NotificationItem[]>(mockNotifications);
  const [detail, setDetail] = useState<NotificationItem | null>(null);

  const grouped = useMemo(
    () => groupByDate(notifications),
    [notifications],
  );

  function openDetail(item: NotificationItem) {
    setDetail(item);
    setNotifications((prev) =>
      prev.map((n) => (n.id === item.id ? { ...n, isRead: true } : n)),
    );
  }

  function closeDetail() {
    setDetail(null);
  }

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <View style={styles.screen}>
          <View style={styles.header}>
            <TouchableOpacity
              style={styles.headerBack}
              onPress={() => router.push("/")}
              accessibilityRole="button"
              accessibilityLabel="Назад"
            >
              <ArrowLeft size={24} color={colors.text} />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Уведомления</Text>
            <View style={styles.headerRight} />
          </View>

          {notifications.length === 0 ? (
            <View style={styles.emptyWrap}>
              <View style={styles.emptyIconCircle}>
                <Bell size={40} color={colors.textMuted} />
              </View>
              <Text style={styles.emptyTitle}>Нет уведомлений</Text>
              <Text style={styles.emptySubtitle}>
                Все уведомления будут появляться здесь
              </Text>
            </View>
          ) : (
            <ScrollView
              style={styles.scroll}
              contentContainerStyle={styles.scrollContent}
              showsVerticalScrollIndicator={false}
            >
              {grouped.map(([dateLabel, list]) => (
                <View key={dateLabel} style={styles.dateBlock}>
                  <Text style={styles.dateHeader}>{dateLabel}</Text>
                  {list.map((item) => {
                    const isWarning = item.type === "warning";
                    const cardBg = isWarning
                      ? colors.warningBg
                      : colors.infoBg;
                    const cardBorder = isWarning
                      ? colors.warningBorder
                      : colors.infoBorder;
                    const iconColor = isWarning
                      ? colors.warning
                      : colors.infoIcon;

                    return (
                      <TouchableOpacity
                        key={item.id}
                        style={[
                          styles.card,
                          {
                            backgroundColor: cardBg,
                            borderColor: cardBorder,
                          },
                          item.isRead && styles.cardRead,
                        ]}
                        activeOpacity={0.85}
                        onPress={() => openDetail(item)}
                      >
                        <View style={styles.cardInner}>
                          <View style={styles.cardIconColumn}>
                            <CardIcon
                              icon={item.icon}
                              color={iconColor}
                              size={22}
                            />
                          </View>
                          <View style={styles.cardBody}>
                            <Text style={styles.cardTitle}>{item.title}</Text>
                            <Text style={styles.cardText}>{item.text}</Text>
                            <Text style={styles.cardTime}>{item.time}</Text>
                          </View>
                          <View style={styles.checkboxWrap}>
                            {item.isRead ? (
                              <View style={styles.checkboxRead}>
                                <Check
                                  size={14}
                                  color={colors.white}
                                  strokeWidth={3}
                                />
                              </View>
                            ) : (
                              <View style={styles.checkboxUnread} />
                            )}
                          </View>
                        </View>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              ))}
            </ScrollView>
          )}
        </View>
      </SafeAreaView>

      <Modal
        visible={detail !== null}
        transparent
        animationType="slide"
        onRequestClose={closeDetail}
      >
        {detail ? (
          <View style={styles.modalRoot}>
            <Pressable
              style={styles.modalBackdrop}
              onPress={closeDetail}
              accessibilityRole="button"
              accessibilityLabel="Закрыть"
            />
            <View style={styles.sheet}>
              <View style={styles.sheetHandle} />
              <View
                style={[
                  styles.detailIconCircle,
                  {
                    backgroundColor:
                      detail.type === "warning"
                        ? colors.warningBg
                        : colors.infoBg,
                  },
                ]}
              >
                <CardIcon
                  icon={detail.icon}
                  color={
                    detail.type === "warning"
                      ? colors.warning
                      : colors.infoIcon
                  }
                  size={40}
                />
              </View>
              <Text style={styles.detailTitle}>{detail.title}</Text>
              <Text style={styles.detailText}>{detail.text}</Text>
              <Text style={styles.detailMeta}>
                {detail.date} · {detail.time}
              </Text>
              <TouchableOpacity
                style={styles.detailButton}
                activeOpacity={0.9}
                onPress={closeDetail}
              >
                <Text style={styles.detailButtonLabel}>Понятно</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : null}
      </Modal>
    </>
  );
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
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    minHeight: 44,
  },
  headerBack: {
    width: 44,
    height: 44,
    alignItems: "flex-start",
    justifyContent: "center",
  },
  headerTitle: {
    flex: 1,
    fontSize: 22,
    fontWeight: "600",
    color: colors.text,
    textAlign: "center",
  },
  headerRight: {
    width: 44,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.xl,
  },
  dateBlock: {
    marginBottom: spacing.md,
  },
  dateHeader: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  card: {
    borderRadius: radius.md,
    borderWidth: 1,
    marginBottom: spacing.sm,
    backgroundColor: colors.card,
  },
  cardRead: {
    opacity: 0.6,
  },
  cardInner: {
    flexDirection: "row",
    alignItems: "flex-start",
    padding: spacing.md,
  },
  cardIconColumn: {
    width: 28,
    alignItems: "center",
    marginRight: spacing.sm,
    paddingTop: 2,
  },
  cardBody: {
    flex: 1,
    minWidth: 0,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
    marginBottom: 4,
  },
  cardText: {
    fontSize: 14,
    fontWeight: "400",
    color: colors.textSecondary,
    marginBottom: 4,
  },
  cardTime: {
    fontSize: 12,
    color: colors.textMuted,
  },
  checkboxWrap: {
    justifyContent: "center",
    paddingLeft: spacing.sm,
  },
  checkboxRead: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxUnread: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: "transparent",
  },
  emptyWrap: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.lg,
  },
  emptyIconCircle: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  emptyTitle: {
    fontSize: 17,
    fontWeight: "600",
    color: colors.text,
    marginBottom: spacing.sm,
    textAlign: "center",
  },
  emptySubtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: "center",
  },
  modalRoot: {
    flex: 1,
    justifyContent: "flex-end",
  },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0, 0, 0, 0.45)",
  },
  sheet: {
    backgroundColor: colors.card,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.xl,
    alignItems: "center",
  },
  sheetHandle: {
    width: 36,
    height: 5,
    borderRadius: 3,
    backgroundColor: colors.border,
    marginBottom: spacing.lg,
  },
  detailIconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  detailTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.text,
    textAlign: "center",
    marginBottom: spacing.sm,
  },
  detailText: {
    fontSize: 15,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: spacing.sm,
  },
  detailMeta: {
    fontSize: 13,
    color: colors.textMuted,
    marginBottom: spacing.lg,
  },
  detailButton: {
    width: "100%",
    backgroundColor: colors.accent,
    borderRadius: radius.lg,
    paddingVertical: spacing.md,
    alignItems: "center",
  },
  detailButtonLabel: {
    fontSize: 17,
    fontWeight: "600",
    color: colors.white,
  },
});
