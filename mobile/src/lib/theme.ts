export const colors = {
  bg: "#F2F2F7",
  card: "#FFFFFF",
  cardAlt: "#F8F8FA",
  accent: "#5CAE5D",
  accentLight: "#7BC67C",
  accentBg: "#E8F5E9",
  text: "#1A1A1A",
  textSecondary: "#6B6B80",
  textMuted: "#AEAEB2",
  border: "#E5E5EA",
  success: "#34C759",
  danger: "#FF3B30",
  warning: "#FF9500",
  white: "#FFFFFF",
  gold: "#5CAE5D",
  goldDark: "#4A9B4B",
  tabBar: "#FFFFFF",
  tabBarBorder: "#E5E5EA",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
} as const;

export const fonts = {
  regular: { fontSize: 14, color: colors.text },
  medium: { fontSize: 16, color: colors.text },
  large: { fontSize: 20, color: colors.text, fontWeight: "600" as const },
  title: { fontSize: 24, color: colors.text, fontWeight: "700" as const },
  caption: { fontSize: 12, color: colors.textSecondary },
} as const;
