import { ConvexProvider, ConvexReactClient } from 'convex/react';
import { useFonts } from 'expo-font';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect } from 'react';
import 'react-native-reanimated';

import { AuthProvider, useAuth } from '@/src/lib/auth-context';

const convex = new ConvexReactClient(process.env.EXPO_PUBLIC_CONVEX_URL!);

export const unstable_settings = {
  anchor: '(tabs)',
};

function RootNavigator() {
  const { auth } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (auth.status === 'loading') return;

    const inAuthGroup = segments[0] === 'auth';

    if (auth.status === 'unauthenticated' && !inAuthGroup) {
      router.replace('/auth/sign-in');
    } else if (auth.status === 'authenticated' && inAuthGroup) {
      router.replace('/(tabs)');
    }
  }, [auth.status, segments]);

  return (
    <>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="auth/sign-in" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding/study" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding/friend" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding/romance" options={{ headerShown: false }} />
        <Stack.Screen
          name="match/[matchId]"
          options={{ title: '匹配详情', headerBackTitle: '返回' }}
        />
        <Stack.Screen
          name="chat/[chatId]"
          options={{ title: '聊天', headerBackTitle: '返回' }}
        />
      </Stack>
      <StatusBar style="auto" />
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    'MaShanZheng-Regular': require('../assets/fonts/MaShanZheng-Regular.ttf'),
    'Caveat-Regular': require('../assets/fonts/Caveat-Regular.ttf'),
  });

  if (!fontsLoaded) return null;

  return (
    <ConvexProvider client={convex}>
      <AuthProvider>
        <RootNavigator />
      </AuthProvider>
    </ConvexProvider>
  );
}
