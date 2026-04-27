import { useAction, useMutation, useQuery } from 'convex/react';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '../../convex/_generated/api';
import { useAuth } from '@/src/lib/auth-context';
import { Colors, Radii, Spacing } from '@/constants/theme';

export default function HomeScreen() {
  const router = useRouter();
  const { auth } = useAuth();
  const userId = auth.status === 'authenticated' ? auth.userId : undefined;

  const user = useQuery(api.auth.me, userId ? { userId } : 'skip');
  const profile = useQuery(api.profile.getProfile, userId ? { userId } : 'skip');
  const digitalHuman = useQuery(api.profile.getDigitalHuman, userId ? { userId } : 'skip');

  const distill = useAction(api.nuwa.distillForUser);
  const [generating, setGenerating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  async function handleGenerate() {
    if (!userId) return;
    setGenerating(true);
    try {
      await distill({ userId });
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  }

  if (!userId) return null;

  const hasProfile = !!profile;
  const hasDH = !!digitalHuman;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => setRefreshing(false)} />}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.greeting}>
          <Text style={styles.greetingText}>
            你好，{user?.nickname ?? '同学'} 👋
          </Text>
          <Text style={styles.schoolText}>{user?.school}</Text>
        </View>

        {!hasProfile ? (
          <View style={styles.ctaCard}>
            <Text style={styles.ctaEmoji}>📝</Text>
            <Text style={styles.ctaTitle}>完成画像问卷，解锁匹配</Text>
            <Text style={styles.ctaDesc}>填写 10 道题，AI 帮你生成专属数字人名片，开始精准匹配</Text>
            <TouchableOpacity
              style={styles.ctaBtn}
              onPress={() => router.push('/onboarding/questionnaire')}
            >
              <Text style={styles.ctaBtnText}>开始填写</Text>
            </TouchableOpacity>
          </View>
        ) : !hasDH ? (
          <View style={styles.ctaCard}>
            <Text style={styles.ctaEmoji}>🤖</Text>
            <Text style={styles.ctaTitle}>生成你的数字人名片</Text>
            <Text style={styles.ctaDesc}>AI 正在蒸馏你的性格画像…</Text>
            <TouchableOpacity
              style={[styles.ctaBtn, generating && styles.ctaBtnDisabled]}
              onPress={handleGenerate}
              disabled={generating}
            >
              {generating ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.ctaBtnText}>立即生成</Text>
              )}
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.dhCard}>
            <View style={styles.dhHeader}>
              <Text style={styles.dhTitle}>我的数字人</Text>
              <TouchableOpacity onPress={() => router.push('/onboarding/questionnaire')}>
                <Text style={styles.dhEdit}>编辑</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.cardTextBox}>
              <Text style={styles.cardText}>{digitalHuman.cardText}</Text>
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionTitle}>心智模型</Text>
              {digitalHuman.mentalModels.map((m, i) => (
                <View key={i} style={styles.tag}>
                  <Text style={styles.tagText}>• {m}</Text>
                </View>
              ))}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionTitle}>表达特征</Text>
              {digitalHuman.expressionPatterns.map((e, i) => (
                <View key={i} style={styles.tag}>
                  <Text style={styles.tagText}>• {e}</Text>
                </View>
              ))}
            </View>

            <TouchableOpacity
              style={[styles.regenBtn, generating && styles.ctaBtnDisabled]}
              onPress={handleGenerate}
              disabled={generating}
            >
              {generating ? (
                <ActivityIndicator color={Colors.primary} size="small" />
              ) : (
                <Text style={styles.regenText}>重新生成</Text>
              )}
            </TouchableOpacity>
          </View>
        )}

        {hasDH && (
          <TouchableOpacity
            style={styles.matchCta}
            onPress={() => router.push('/(tabs)/match')}
          >
            <Text style={styles.matchCtaText}>去看看谁和你匹配 ✨</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  content: { padding: Spacing.lg, gap: Spacing.lg },
  greeting: { gap: Spacing.xs },
  greetingText: { fontSize: 24, fontWeight: '800', color: Colors.text },
  schoolText: { fontSize: 14, color: Colors.textSecondary },
  ctaCard: {
    backgroundColor: Colors.card,
    borderRadius: Radii.xl,
    padding: Spacing.xl,
    alignItems: 'center',
    gap: Spacing.sm,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  ctaEmoji: { fontSize: 48 },
  ctaTitle: { fontSize: 18, fontWeight: '700', color: Colors.text, textAlign: 'center' },
  ctaDesc: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: 20 },
  ctaBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radii.lg,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    marginTop: Spacing.sm,
  },
  ctaBtnDisabled: { opacity: 0.5 },
  ctaBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  dhCard: {
    backgroundColor: Colors.card,
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    gap: Spacing.md,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  dhHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  dhTitle: { fontSize: 18, fontWeight: '700', color: Colors.text },
  dhEdit: { fontSize: 14, color: Colors.primary, fontWeight: '600' },
  cardTextBox: {
    backgroundColor: Colors.primary + '10',
    borderRadius: Radii.md,
    padding: Spacing.md,
    borderLeftWidth: 3,
    borderLeftColor: Colors.primary,
  },
  cardText: { fontSize: 15, color: Colors.text, lineHeight: 22 },
  section: { gap: Spacing.xs },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: Colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 },
  tag: {},
  tagText: { fontSize: 14, color: Colors.textSecondary, lineHeight: 20 },
  regenBtn: {
    borderWidth: 1.5,
    borderColor: Colors.primary,
    borderRadius: Radii.lg,
    padding: Spacing.sm,
    alignItems: 'center',
  },
  regenText: { fontSize: 14, color: Colors.primary, fontWeight: '600' },
  matchCta: {
    backgroundColor: Colors.primary,
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    alignItems: 'center',
  },
  matchCtaText: { fontSize: 16, color: '#fff', fontWeight: '700' },
});
