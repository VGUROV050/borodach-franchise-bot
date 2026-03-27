import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { FloatingMenu } from "@/components/FloatingMenu";
import { colors } from "@/lib/theme";

const headerOptions = {
  headerStyle: { backgroundColor: colors.bg },
  headerTintColor: colors.text,
  headerTitleStyle: { fontWeight: "700" as const, fontSize: 18 },
  headerShadowVisible: false,
};

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ contentStyle: { backgroundColor: colors.bg }, ...headerOptions }}>
        <Stack.Screen name="index" options={{ headerTitle: "BORODACH" }} />
        <Stack.Screen name="stats" options={{ headerTitle: "Статистика" }} />
        <Stack.Screen name="tasks" options={{ headerTitle: "Задачи" }} />
        <Stack.Screen name="rating" options={{ headerTitle: "Рейтинг" }} />
        <Stack.Screen name="useful" options={{ headerTitle: "Полезное" }} />
        <Stack.Screen name="ai-chat" options={{ headerTitle: "AI-ассистент" }} />
        <Stack.Screen name="contact" options={{ headerTitle: "Связь с офисом" }} />
        <Stack.Screen name="polls" options={{ headerTitle: "Опросы" }} />
        <Stack.Screen name="profile-screen" options={{ headerTitle: "Профиль" }} />
        <Stack.Screen name="create-task" options={{ headerTitle: "Новая задача", presentation: "modal" }} />
      </Stack>
      <FloatingMenu />
    </>
  );
}
