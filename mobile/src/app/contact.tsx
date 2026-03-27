import React from "react";
import { ScrollView, Text, StyleSheet, RefreshControl } from "react-native";
import { Stack } from "expo-router";
import { Card } from "@/components/ui/Card";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { colors, spacing, fonts } from "@/lib/theme";

export default function ContactScreen() {
  const { data, loading, error, refresh } = useApi(() => api.getContactInfo());

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorMessage message={error} onRetry={refresh} />;

  return (
    <>
      <Stack.Screen options={{ headerTitle: "Связь с офисом" }} />
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
        <Text style={styles.icon}>📞</Text>
        <Text style={styles.title}>Связь с офисом</Text>
        <Card>
          <Text style={styles.text} selectable>
            {data?.text ?? ""}
          </Text>
        </Card>
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
    paddingBottom: 100,
    alignItems: "center",
  },
  icon: {
    fontSize: 48,
    marginTop: spacing.lg,
  },
  title: {
    ...fonts.title,
    textAlign: "center",
  },
  text: {
    ...fonts.regular,
    lineHeight: 22,
  },
});
