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
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  accent: {
    borderColor: colors.accent,
    borderWidth: 0.5,
  },
});
