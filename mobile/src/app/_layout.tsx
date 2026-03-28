import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { FloatingMenu } from "@/components/FloatingMenu";
import { colors } from "@/lib/theme";

const headerOptions = {
  headerStyle: { backgroundColor: colors.bg },
  headerTintColor: colors.text,
  headerTitleStyle: { fontWeight: "700" as const, fontSize: 18 },
  headerShadowVisible: false,
  headerBackVisible: false,
  headerLeft: () => null,
  gestureEnabled: false,
};

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ contentStyle: { backgroundColor: colors.bg }, ...headerOptions }}>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="stats" options={{ headerShown: false }} />
        <Stack.Screen name="tasks" options={{ headerShown: false }} />
        <Stack.Screen name="rating" options={{ headerShown: false }} />
        <Stack.Screen name="useful" options={{ headerShown: false }} />
        <Stack.Screen name="ai-chat" options={{ headerShown: false }} />
        <Stack.Screen name="contact" options={{ headerShown: false }} />
        <Stack.Screen name="polls" options={{ headerShown: false }} />
        <Stack.Screen name="notifications" options={{ headerShown: false }} />
        <Stack.Screen name="profile-screen" options={{ headerShown: false }} />
        <Stack.Screen
          name="create-task"
          options={{
            headerShown: false,
            presentation: "transparentModal",
            animation: "slide_from_bottom",
          }}
        />
      </Stack>
      <FloatingMenu />
    </>
  );
}
