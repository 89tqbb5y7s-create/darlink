import { useMutation, useQuery } from 'convex/react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '../../convex/_generated/api';
import type { Id } from '../../convex/_generated/dataModel';
import { useAuth } from '@/src/lib/auth-context';
import { Colors, Radii, Spacing } from '@/constants/theme';

export default function MatchDetailScreen() {
  const { matchId } = useLocalSearchParams<{ matchId: string }>();
  const router = useRouter();
  const { auth } = useAuth();
  const userId = auth.status === 'authenticated' ? auth.userId : undefined;

  const detail = useQuery(
    api.matches.getDetail,
    matchId ? { matchId: matchId as Id<'matches'> } : 'skip'
  );
  const respond = useMutation(api.matches.respond);
  const [responding, setResponding] = useState(false);
  const [selectedIce, setSelectedIce] = useState<number | null>(null);

  if (!userId || !detail) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator style={{ marginTop: 80 }} color={Colors.primary} />
      </SafeAreaView>
    );
  }

  const { match, userA, userB } = detail;
  const isA = match.userIdA === userId;
  const myStatus = isA ? match.aStatus : match.bStatus;
  const otherUser = isA ? userB : userA;
  const isMutual = match.aStatus === 'interested' && match.bStatus === 'interested';

  async function handleDecision(decision: 'interested' | 'passed') {
    if (!matchId || !userId) return;
    setResponding(true);
    try {
      const result = await respond({
        matchId: matchId as Id<'matches'>,
        userId,
        decision,
      }) as { match: unknown; chatId: string | null };
      if (decision === 'interested' && result.chatId) {
        Alert.alert('🎉 双向心动！', '你们已经互相心动，现在可以开始聊天了', [
          { text: '去聊天', onPress: () => router.replace(`/chat/${result.chatId}`) },
        ]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setResponding(false);
    }
  }

  const sceneColor = match.scene === 'study' ? Colors.study : match.scene === 'food' ? Colors.food : Colors.romance;
  const sceneLabel = match.scene === 'study' ? '学习搭子' : match.scene === 'food' ? '饭搭子' : '恋爱';

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.topCard}>
          <View style={[styles.sceneChip, { backgroundColor: sceneColor + '20' }]}>
            <Text style={[styles.sceneText, { color: sceneColor }]}>{sceneLabel}</Text>
          </View>

          <View style={styles.userRow}>
            <View style={[styles.avatar, { backgroundColor: sceneColor + '20' }]}>
              <Text style={[styles.avatarText, { color: sceneColor }]}>
                {otherUser?.nickname?.[0] ?? '?'}
              </Text>
            </View>
            <View style={styles.userInfo}>
              <Text style={styles.userName}>{otherUser?.nickname}</Text>
              <Text style={styles.userSchool}>{otherUser?.school}</Text>
            </View>
            <View style={styles.scoreCircle}>
              <Text style={[styles.scoreNum, { color: sceneColor }]}>{match.fitScore}</Text>
              <Text style={styles.scoreLabel}>分</Text>
            </View>
          </View>
        </View>

        <View style={styles.reportCard}>
          <Text style={styles.sectionTitle}>匹配报告</Text>
          <Text style={styles.explanation}>{match.explanation}</Text>

          {match.sharedTopics.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.secLabel}>共同话题</Text>
              <View style={styles.tagRow}>
                {match.sharedTopics.map((t) => (
                  <View key={t} style={[styles.chip, { backgroundColor: Colors.success + '15' }]}>
                    <Text style={[styles.chipText, { color: Colors.success }]}>{t}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          {match.complementarities.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.secLabel}>互补之处</Text>
              {match.complementarities.map((c, i) => (
                <Text key={i} style={styles.bulletText}>• {c}</Text>
              ))}
            </View>
          )}

          {match.risks.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.secLabel}>需要注意</Text>
              {match.risks.map((r, i) => (
                <Text key={i} style={[styles.bulletText, { color: Colors.warning }]}>⚠ {r}</Text>
              ))}
            </View>
          )}
        </View>

        {match.icebreakers.length > 0 && (
          <View style={styles.iceCard}>
            <Text style={styles.sectionTitle}>AI 破冰建议</Text>
            <Text style={styles.iceHint}>选一句发给对方（由你确认后才会出现在聊天框）</Text>
            {match.icebreakers.map((ice, i) => (
              <TouchableOpacity
                key={i}
                style={[
                  styles.iceOption,
                  selectedIce === i && { borderColor: Colors.primary, backgroundColor: Colors.primary + '08' }
                ]}
                onPress={() => setSelectedIce(selectedIce === i ? null : i)}
              >
                <Text style={[styles.iceText, selectedIce === i && { color: Colors.primary }]}>
                  "{ice}"
                </Text>
                {selectedIce === i && <Text style={styles.iceSelected}>✓ 已选</Text>}
              </TouchableOpacity>
            ))}
          </View>
        )}
      </ScrollView>

      {!isMutual && myStatus === 'new' && (
        <View style={styles.footer}>
          <TouchableOpacity
            style={styles.passBtn}
            onPress={() => handleDecision('passed')}
            disabled={responding}
          >
            <Text style={styles.passBtnText}>跳过</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.interestedBtn, responding && styles.btnDisabled]}
            onPress={() => handleDecision('interested')}
            disabled={responding}
          >
            {responding ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.interestedBtnText}>心动 ✨</Text>
            )}
          </TouchableOpacity>
        </View>
      )}

      {isMutual && (
        <View style={styles.footer}>
          <TouchableOpacity
            style={styles.chatBtn}
            onPress={() => router.push('/(tabs)/chat')}
          >
            <Text style={styles.chatBtnText}>🎉 去聊天</Text>
          </TouchableOpacity>
        </View>
      )}

      {!isMutual && myStatus !== 'new' && (
        <View style={styles.footerInfo}>
          <Text style={styles.footerInfoText}>
            {myStatus === 'interested' ? '你已表示心动，等待对方决定…' : '已跳过此匹配'}
          </Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  content: { padding: Spacing.lg, gap: Spacing.lg, paddingBottom: Spacing.xxl },
  topCard: {
    backgroundColor: Colors.card,
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    gap: Spacing.md,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  sceneChip: { alignSelf: 'flex-start', paddingHorizontal: Spacing.md, paddingVertical: 4, borderRadius: Radii.full },
  sceneText: { fontSize: 13, fontWeight: '700' },
  userRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  avatar: { width: 56, height: 56, borderRadius: 28, alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: 24, fontWeight: '700' },
  userInfo: { flex: 1 },
  userName: { fontSize: 20, fontWeight: '800', color: Colors.text },
  userSchool: { fontSize: 14, color: Colors.textSecondary },
  scoreCircle: { alignItems: 'center' },
  scoreNum: { fontSize: 32, fontWeight: '800' },
  scoreLabel: { fontSize: 12, color: Colors.textMuted },
  reportCard: {
    backgroundColor: Colors.card,
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    gap: Spacing.md,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: Colors.text },
  explanation: { fontSize: 15, color: Colors.textSecondary, lineHeight: 22 },
  section: { gap: Spacing.xs },
  secLabel: { fontSize: 13, fontWeight: '700', color: Colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  chip: { paddingHorizontal: Spacing.sm, paddingVertical: 4, borderRadius: Radii.full },
  chipText: { fontSize: 13, fontWeight: '600' },
  bulletText: { fontSize: 14, color: Colors.textSecondary, lineHeight: 20 },
  iceCard: {
    backgroundColor: Colors.card,
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    gap: Spacing.md,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  iceHint: { fontSize: 13, color: Colors.textMuted },
  iceOption: {
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: Radii.md,
    padding: Spacing.md,
    gap: 4,
  },
  iceText: { fontSize: 14, color: Colors.text, lineHeight: 20 },
  iceSelected: { fontSize: 12, color: Colors.primary, fontWeight: '600' },
  footer: {
    flexDirection: 'row',
    gap: Spacing.sm,
    padding: Spacing.lg,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.bg,
  },
  passBtn: {
    flex: 1,
    padding: Spacing.md,
    borderRadius: Radii.lg,
    borderWidth: 1.5,
    borderColor: Colors.border,
    alignItems: 'center',
  },
  passBtnText: { fontSize: 15, color: Colors.textSecondary, fontWeight: '600' },
  interestedBtn: { flex: 2, padding: Spacing.md, borderRadius: Radii.lg, backgroundColor: Colors.primary, alignItems: 'center' },
  btnDisabled: { opacity: 0.5 },
  interestedBtnText: { fontSize: 15, color: '#fff', fontWeight: '700' },
  chatBtn: { flex: 1, padding: Spacing.md, borderRadius: Radii.lg, backgroundColor: Colors.success, alignItems: 'center' },
  chatBtnText: { fontSize: 15, color: '#fff', fontWeight: '700' },
  footerInfo: { padding: Spacing.lg, alignItems: 'center', borderTopWidth: 1, borderTopColor: Colors.border },
  footerInfoText: { fontSize: 14, color: Colors.textMuted },
});
