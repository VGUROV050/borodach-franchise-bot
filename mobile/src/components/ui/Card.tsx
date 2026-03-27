import React from "react";
import { View, StyleSheet, ViewProps } from "react-native";
import { colors, radius, spacing } from "@/lib/theme";

interface CardProps extends ViewProps {
  variant?: "default" | "accent";
}

export function Card({ style, variant = "default", children, ...rest }: CardProps) {
  return (
    <View
      style={[
        styles.card,
        variant === "accent" && styles.accent,
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  accent: {
    borderColor: colors.gold,
    borderWidth: 1.5,
  },
});
