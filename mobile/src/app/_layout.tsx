import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { colors } from "@/lib/theme";

const stackHeaderOptions = {
  headerStyle: { backgroundColor: colors.bg },
  headerTintColor: colors.text,
  headerTitleStyle: { fontWeight: "700" as const, fontSize: 18 },
  headerShadowVisible: false,
};

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="profile-screen"
          options={{ headerShown: true, ...stackHeaderOptions }}
        />
        <Stack.Screen
          name="create-task"
          options={{
            headerShown: true,
            presentation: "modal",
            ...stackHeaderOptions,
          }}
        />
        <Stack.Screen
          name="useful"
          options={{ headerShown: true, ...stackHeaderOptions }}
        />
        <Stack.Screen
          name="ai-chat"
          options={{ headerShown: true, ...stackHeaderOptions }}
        />
        <Stack.Screen
          name="contact"
          options={{ headerShown: true, ...stackHeaderOptions }}
        />
        <Stack.Screen
          name="polls"
          options={{ headerShown: true, ...stackHeaderOptions }}
        />
      </Stack>
    </>
  );
}
