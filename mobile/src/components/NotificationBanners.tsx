import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";
import { colors, spacing, radius } from "@/lib/theme";

export interface NotificationItem {
  id: number;
  title: string;
  text: string;
  type: "info" | "warning" | "success";
  dismissible: boolean;
}

const MOCK_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 1,
    title: "Роялти за март",
    text: "Срок оплаты роялти до 5 апреля. Не забудьте произвести оплату вовремя.",
    type: "warning",
    dismissible: true,
  },
  {
    id: 2,
    title: "Новая акция для клиентов",
    text: "Подключите весеннюю акцию «Стрижка + уход» со скидкой 20% для привлечения новых клиентов.",
    type: "info",
    dismissible: true,
  },
];

const TYPE_CONFIG = {
  info: {
    bg: "#EDF4FF",
    border: "#C2D9FF",
    icon: "ℹ️",
    titleColor: "#1A5CBA",
  },
  warning: {
    bg: "#FFF8E6",
    border: "#FFE4A0",
    icon: "⚠️",
    titleColor: "#996B00",
  },
  success: {
    bg: colors.accentBg,
    border: "#B8E6B8",
    icon: "✅",
    titleColor: colors.accent,
  },
} as const;

interface Props {
  notifications?: NotificationItem[];
}

export function NotificationBanners({ notifications = MOCK_NOTIFICATIONS }: Props) {
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());

  const visible = notifications.filter((n) => !dismissed.has(n.id));
  if (visible.length === 0) return null;

  function dismiss(id: number) {
    setDismissed((prev) => new Set(prev).add(id));
  }

  return (
    <View style={styles.container}>
      {visible.map((item) => {
        const cfg = TYPE_CONFIG[item.type];
        return (
          <View
            key={item.id}
            style={[
              styles.banner,
              { backgroundColor: cfg.bg, borderColor: cfg.border },
            ]}
          >
            <View style={styles.row}>
              <Text style={styles.icon}>{cfg.icon}</Text>
              <View style={styles.textWrap}>
                <Text style={[styles.title, { color: cfg.titleColor }]}>
                  {item.title}
                </Text>
                <Text style={styles.text}>{item.text}</Text>
              </View>
              {item.dismissible && (
                <TouchableOpacity
                  style={styles.closeBtn}
                  onPress={() => dismiss(item.id)}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <Text style={styles.closeText}>✕</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  banner: {
    borderRadius: radius.md,
    borderWidth: 0.5,
    padding: spacing.md,
  },
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
  },
  icon: {
    fontSize: 18,
    marginTop: 1,
  },
  textWrap: {
    flex: 1,
  },
  title: {
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 3,
  },
  text: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  closeBtn: {
    padding: 2,
  },
  closeText: {
    fontSize: 14,
    color: colors.textMuted,
    fontWeight: "500",
  },
});
