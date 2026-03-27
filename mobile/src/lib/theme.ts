// BORODACH dark theme — barbershop aesthetic

export const colors = {
  bg: "#0F0F1A",
  card: "#1A1A2E",
  cardAlt: "#16213E",
  accent: "#C9A84C",
  accentLight: "#E8D48B",
  text: "#EAEAEA",
  textSecondary: "#8E8E9A",
  textMuted: "#5A5A6A",
  border: "#2A2A3E",
  success: "#4CAF50",
  danger: "#F44336",
  warning: "#FF9800",
  white: "#FFFFFF",
  gold: "#C9A84C",
  goldDark: "#A68732",
  tabBar: "#12121F",
  tabBarBorder: "#1E1E30",
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
