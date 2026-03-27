import { Tabs } from "expo-router";
import { Text, StyleSheet } from "react-native";
import { colors } from "@/lib/theme";

function tabIcon(icon: string, focused: boolean) {
  return <Text style={[styles.icon, focused && styles.iconActive]}>{icon}</Text>;
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: {
          backgroundColor: colors.bg,
          shadowColor: "transparent",
          elevation: 0,
        },
        headerTitleStyle: {
          color: colors.text,
          fontWeight: "700",
          fontSize: 18,
        },
        tabBarStyle: {
          backgroundColor: colors.tabBar,
          borderTopColor: colors.tabBarBorder,
          borderTopWidth: 1,
          height: 85,
          paddingBottom: 20,
          paddingTop: 8,
        },
        tabBarActiveTintColor: colors.gold,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Главная",
          headerTitle: "BORODACH",
          tabBarIcon: ({ focused }) => tabIcon("🏠", focused),
        }}
      />
      <Tabs.Screen
        name="stats"
        options={{
          title: "Статистика",
          headerTitle: "Статистика",
          tabBarIcon: ({ focused }) => tabIcon("📊", focused),
        }}
      />
      <Tabs.Screen
        name="rating"
        options={{
          title: "Рейтинг",
          headerTitle: "Рейтинг сети",
          tabBarIcon: ({ focused }) => tabIcon("🏆", focused),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Профиль",
          headerTitle: "Профиль",
          tabBarIcon: ({ focused }) => tabIcon("👤", focused),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  icon: {
    fontSize: 22,
    opacity: 0.5,
  },
  iconActive: {
    opacity: 1,
  },
});
