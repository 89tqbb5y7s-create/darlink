import { useAction, useQuery } from 'convex/react';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '../../convex/_generated/api';
import { useAuth } from '@/src/lib/auth-context';
import { Colors, Radii, Shadows, Spacing } from '@/constants/theme';
import { PressableScale } from '@/src/components/PressableScale';
import * as Haptics from 'expo-haptics';

function Tag({ text, color }: { text: string; color: string }) {
  return (
    <View style={[styles.tag, { backgroundColor: color + '15', borderColor: color + '30' }]}>
      <Text style={[styles.tagText, { color }]}>{text}</Text>
    </View>
  );
}

export default function HomeScreen() {
  const router = useRouter();
  const { auth } = useAuth();
  const userId = auth.status === 'authenticated' ? auth.userId : undefined;

  const user = useQuery(api.auth.me, userId ? { userId } : 'skip');
  const profile = useQuery(api.profile.getProfile, userId ? { userId } : 'skip');
  const dh = useQuery(api.profile.getDigitalHuman, userId ? { userId } : 'skip');
  const distill = useAction(api.nuwa.distillForUser);
  const generateMatches = useAction(api.matchEngine.generateForUser);
  const [generating, setGenerating] = useState(false);

  if (!userId) return null;

  async function handleGenerate() {
    if (!userId) return;
    setGenerating(true);
    try {
      await distill({ userId });
      // Fire match generation after digital human; don't block UI on result
      generateMatches({ userId }).catch((e) => console.error('match gen:', e));
    } catch (e) { console.error(e); }
    finally { setGenerating(false); }
  }

  const hasProfile = !!profile;
  const hasDH = !!dh;

  return (
    <SafeAreaView style={styles.container}>
      {/* Background orbs */}
      <View style={styles.orb1} pointerEvents="none" />
      <View style={styles.orb2} pointerEvents="none" />

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>

        {/* Header greeting */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>你好，{user?.nickname ?? '同学'} 👋</Text>
            <Text style={styles.school}>{user?.school}</Text>
          </View>
          {user?.verifiedStatus === 'verified' && (
            <View style={styles.verifiedBadge}>
              <Text style={styles.verifiedText}>✓ 已认证</Text>
            </View>
          )}
        </View>

        {/* Step 1: No profile yet */}
        {!hasProfile && (
          <View style={styles.stepCard}>
            <LinearGradient
              colors={['#FDF2F8', '#EEF2FF']}
              style={styles.stepGrad}
            >
              <Text style={styles.stepEmoji}>📝</Text>
              <Text style={styles.stepTitle}>第一步：完成画像问卷</Text>
              <Text style={styles.stepDesc}>5 分钟轻量问卷，AI 帮你生成专属数字人名片，才能开始精准匹配</Text>
              <PressableScale onPress={() => router.push('/onboarding/questionnaire')} style={styles.stepBtnWrap} haptic="medium" scaleDown={0.97}>
                <LinearGradient colors={[Colors.gradientStart, Colors.gradientEnd]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.stepBtn}>
                  <Text style={styles.stepBtnText}>开始填写 ✦</Text>
                </LinearGradient>
              </PressableScale>
            </LinearGradient>
          </View>
        )}

        {/* Step 2: Profile done, no digital human yet */}
        {hasProfile && !hasDH && (
          <View style={styles.stepCard}>
            <LinearGradient colors={['#FDF2F8', '#EEF2FF']} style={styles.stepGrad}>
              <Text style={styles.stepEmoji}>🤖</Text>
              <Text style={styles.stepTitle}>第二步：生成你的 AI 数字人</Text>
              <Text style={styles.stepDesc}>AI 正在蒸馏你的性格画像，生成专属名片…</Text>
              <PressableScale onPress={handleGenerate} disabled={generating} style={styles.stepBtnWrap} haptic="medium" scaleDown={0.97}>
                <LinearGradient colors={[Colors.gradientStart, Colors.gradientEnd]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={[styles.stepBtn, generating && { opacity: 0.5 }]}>
                  {generating ? <ActivityIndicator color="#fff" /> : <Text style={styles.stepBtnText}>立即生成 ✦</Text>}
                </LinearGradient>
              </PressableScale>
            </LinearGradient>
          </View>
        )}

        {/* Digital Human Card */}
        {hasDH && (
          <>
            <View style={styles.dhCard}>
              <View style={styles.dhCardHeader}>
                <View style={styles.dhAvatarWrap}>
                  <LinearGradient colors={[Colors.gradientStart, Colors.gradientEnd]} style={styles.dhAvatar}>
                    <Text style={styles.dhAvatarText}>{user?.nickname?.[0] ?? '?'}</Text>
                  </LinearGradient>
                  <View style={styles.dhSparkle}>
                    <Text style={{ fontSize: 10 }}>✦</Text>
                  </View>
                </View>
                <View style={styles.dhMeta}>
                  <Text style={styles.dhName}>{user?.nickname}</Text>
                  <Text style={styles.dhSchool}>{user?.school}</Text>
                </View>
                <PressableScale onPress={() => router.push('/onboarding/questionnaire')} style={styles.dhEditBtn} haptic="light">
                  <Text style={styles.dhEditText}>编辑</Text>
                </PressableScale>
              </View>

              <View style={styles.dhTextBox}>
                <Text style={styles.dhCardText}>{dh.cardText}</Text>
              </View>

              <View style={styles.dhSection}>
                <Text style={styles.dhSectionLabel}>心智模型</Text>
                <View style={styles.tagRow}>
                  {dh.mentalModels.map((m, i) => (
                    <Tag key={i} text={m} color={Colors.study} />
                  ))}
                </View>
              </View>

              <View style={styles.dhSection}>
                <Text style={styles.dhSectionLabel}>表达特征</Text>
                <View style={styles.tagRow}>
                  {dh.expressionPatterns.map((e, i) => (
                    <Tag key={i} text={e} color={Colors.pinkDeep} />
                  ))}
                </View>
              </View>

              <PressableScale onPress={handleGenerate} disabled={generating} style={styles.regenBtn} haptic="light">
                {generating
                  ? <ActivityIndicator color={Colors.pinkDeep} size="small" />
                  : <Text style={styles.regenText}>重新生成</Text>
                }
              </PressableScale>
            </View>

            {/* Go Match CTA */}
            <PressableScale onPress={() => router.push('/(tabs)/match')} style={styles.matchCtaWrap} haptic="heavy" scaleDown={0.97}>
              <LinearGradient
                colors={[Colors.gradientStart, Colors.gradientEnd]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.matchCta}
              >
                <Text style={styles.matchCtaText}>去看看谁和你匹配</Text>
                <Text style={styles.matchCtaIcon}>✨</Text>
              </LinearGradient>
            </PressableScale>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  orb1: {
    position: 'absolute', top: -40, right: -40, width: 220, height: 220,
    borderRadius: 110, backgroundColor: Colors.pink, opacity: 0.10,
  },
  orb2: {
    position: 'absolute', bottom: 120, left: -60, width: 200, height: 200,
    borderRadius: 100, backgroundColor: Colors.blue, opacity: 0.08,
  },
  content: { padding: Spacing.lg, gap: Spacing.lg, paddingBottom: Spacing.xxl },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  greeting: { fontSize: 26, fontWeight: '800', color: Colors.text },
  school: { fontSize: 13, color: Colors.textSecondary, marginTop: 2 },
  verifiedBadge: {
    backgroundColor: Colors.successBg,
    borderRadius: Radii.full,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  verifiedText: { fontSize: 12, color: Colors.success, fontWeight: '600' },

  stepCard: { borderRadius: Radii['3xl'], overflow: 'hidden', ...Shadows.md },
  stepGrad: { padding: Spacing.xl, alignItems: 'center', gap: Spacing.md },
  stepEmoji: { fontSize: 48 },
  stepTitle: { fontSize: 18, fontWeight: '800', color: Colors.text, textAlign: 'center' },
  stepDesc: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: 20 },
  stepBtnWrap: { width: '100%' },
  stepBtn: { borderRadius: Radii.full, padding: Spacing.md, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6 },
  stepBtnText: { color: '#fff', fontSize: 16, fontWeight: '800' },

  dhCard: {
    backgroundColor: Colors.bgWhite,
    borderRadius: Radii['3xl'],
    padding: Spacing.lg,
    gap: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.md,
  },
  dhCardHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  dhAvatarWrap: { position: 'relative' },
  dhAvatar: { width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center' },
  dhAvatarText: { fontSize: 22, fontWeight: '800', color: '#fff' },
  dhSparkle: {
    position: 'absolute', bottom: -2, right: -2,
    width: 18, height: 18, borderRadius: 9,
    backgroundColor: '#fff',
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Colors.border,
  },
  dhMeta: { flex: 1 },
  dhName: { fontSize: 17, fontWeight: '800', color: Colors.text },
  dhSchool: { fontSize: 12, color: Colors.textSecondary },
  dhEditBtn: {
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: Radii.full,
    paddingHorizontal: 12,
    paddingVertical: 5,
  },
  dhEditText: { fontSize: 13, color: Colors.textSecondary, fontWeight: '600' },
  dhTextBox: {
    backgroundColor: Colors.bg,
    borderRadius: Radii.lg,
    padding: Spacing.md,
    borderLeftWidth: 3,
    borderLeftColor: Colors.pink,
  },
  dhCardText: { fontSize: 14, color: Colors.textBody, lineHeight: 22 },
  dhSection: { gap: 6 },
  dhSectionLabel: { fontSize: 11, fontWeight: '700', color: Colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.8 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  tag: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: Radii.full, borderWidth: 1 },
  tagText: { fontSize: 12, fontWeight: '600' },
  regenBtn: {
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: Radii.full,
    padding: Spacing.sm,
    alignItems: 'center',
  },
  regenText: { fontSize: 13, color: Colors.textSecondary, fontWeight: '600' },
  matchCtaWrap: { borderRadius: Radii.full, overflow: 'hidden' },
  matchCta: {
    padding: Spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: Radii.full,
    ...Shadows.lg,
  },
  matchCtaText: { fontSize: 16, color: '#fff', fontWeight: '800' },
  matchCtaIcon: { fontSize: 18 },
});
