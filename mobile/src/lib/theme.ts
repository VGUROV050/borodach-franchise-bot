export const colors = {
  bg: "#F2F2F7",
  card: "#FFFFFF",
  cardAlt: "#E5E5EA",
  accent: "#5CAE5D",
  accentLight: "rgba(92, 174, 93, 0.1)",
  accentBg: "#E8F5E9",
  text: "#1A1A1A",
  textSecondary: "#6B6B80",
  textMuted: "#AEAEB2",
  border: "#E5E5EA",
  success: "#34C759",
  danger: "#FF3B30",
  warning: "#F59E0B",
  white: "#FFFFFF",
  gold: "#FFD700",
  silver: "#C0C0C0",
  bronze: "#CD7F32",
  infoBg: "#EDF4FF",
  infoBorder: "#C2D9FF",
  infoIcon: "#3B82F6",
  warningBg: "#FFF8E6",
  warningBorder: "#FFE4A0",
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
  title: { fontSize: 28, color: colors.text, fontWeight: "600" as const },
  caption: { fontSize: 12, color: colors.textSecondary },
  screenTitle: { fontSize: 28, fontWeight: "600" as const, color: colors.text },
} as const;
