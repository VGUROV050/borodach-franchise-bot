import React, { useMemo } from "react";
import {
  ScrollView,
  Text,
  StyleSheet,
  RefreshControl,
  View,
  Linking,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Phone } from "lucide-react-native";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";

const HEADER_ICON = 32;
const ACCENT = "#5CAE5D";
function parseContactSections(text: string): { title: string; body: string }[] {
  const raw = text.trim();
  if (!raw) return [];

  const blocks = raw.split(/\n{2,}/);
  const out: { title: string; body: string }[] = [];

  for (const block of blocks) {
    const lines = block.split(/\n/).map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) continue;
    const first = lines[0];
    const upper = first.replace(/[:：]\s*$/, "");
    const looksLikeTitle =
      lines.length > 1 &&
      upper.length >= 3 &&
      upper.length <= 48 &&
      (upper === upper.toUpperCase() ||
        /^(телефон|email|адрес|часы|полезные|сайт|контакт)/i.test(upper));

    if (looksLikeTitle) {
      out.push({
        title: upper.replace(/[:：]\s*$/, ""),
        body: lines.slice(1).join("\n"),
      });
    } else {
      out.push({ title: "", body: lines.join("\n") });
    }
  }

  if (out.length === 0) return [{ title: "", body: raw }];
  return out;
}

function openUrl(href: string) {
  Linking.openURL(href).catch(() => {});
}

function LinkifiedParagraph({ text }: { text: string }) {
  const parts = text.split(/(\+?\d[\d\s\-()]{8,}\d|mailto:[^\s]+|https?:\/\/[^\s]+)/gi);
  return (
    <Text style={styles.sectionBody} selectable>
      {parts.map((part, i) => {
        if (/^https?:\/\//i.test(part)) {
          return (
            <Text
              key={i}
              style={styles.link}
              onPress={() => openUrl(part)}
            >
              {part}
            </Text>
          );
        }
        if (/^mailto:/i.test(part)) {
          return (
            <Text
              key={i}
              style={styles.link}
              onPress={() => openUrl(part)}
            >
              {part.replace(/^mailto:/i, "")}
            </Text>
          );
        }
        if (/^\+?\d[\d\s\-()]{8,}\d$/.test(part.replace(/\s/g, ""))) {
          const tel = part.replace(/[^\d+]/g, "");
          const href = tel.startsWith("+") ? `tel:${tel}` : `tel:${tel}`;
          return (
            <Text key={i} style={styles.link} onPress={() => openUrl(href)}>
              {part}
            </Text>
          );
        }
        return <Text key={i}>{part}</Text>;
      })}
    </Text>
  );
}

export default function ContactScreen() {
  const { data, loading, error, refresh } = useApi(() => api.getContactInfo());

  const sections = useMemo(
    () => parseContactSections(data?.text ?? ""),
    [data?.text],
  );

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorMessage message={error} onRetry={refresh} />;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.header}>
        <Phone size={HEADER_ICON} color={ACCENT} strokeWidth={2} />
        <Text style={styles.headerTitle}>Связь с офисом</Text>
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
        <View style={styles.card}>
          {sections.map((sec, idx) => (
            <View key={`${sec.title}-${idx}`}>
              {idx > 0 && <View style={styles.divider} />}
              {sec.title ? (
                <Text style={styles.sectionLabel}>{sec.title}</Text>
              ) : null}
              <LinkifiedParagraph text={sec.body} />
            </View>
          ))}
        </View>
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
    paddingBottom: 100,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.md,
    padding: spacing.md,
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.06,
        shadowRadius: 8,
      },
      android: { elevation: 2 },
      default: {},
    }),
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.border,
    marginVertical: spacing.md,
  },
  sectionLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textSecondary,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: spacing.sm,
  },
  sectionBody: {
    ...fonts.regular,
    lineHeight: 22,
    color: colors.text,
  },
  link: {
    color: ACCENT,
    fontWeight: "500",
  },
});
