import { useQuery } from 'convex/react';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
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

type Scene = 'study' | 'food' | 'romance';

const SCENES: { key: Scene; label: string; color: string; emoji: string }[] = [
  { key: 'study', label: '学习搭子', color: Colors.study, emoji: '📚' },
  { key: 'food', label: '饭搭子', color: Colors.food, emoji: '🍜' },
  { key: 'romance', label: '恋爱', color: Colors.romance, emoji: '💕' },
];

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  return (
    <View style={sb.container}>
      <View style={[sb.fill, { width: `${pct}%` }]} />
    </View>
  );
}
const sb = StyleSheet.create({
  container: { height: 6, backgroundColor: Colors.border, borderRadius: 3, overflow: 'hidden', flex: 1 },
  fill: { height: 6, backgroundColor: Colors.primary, borderRadius: 3 },
});

export default function MatchScreen() {
  const router = useRouter();
  const { auth } = useAuth();
  const userId = auth.status === 'authenticated' ? auth.userId : undefined;
  const [scene, setScene] = useState<Scene>('study');

  const matches = useQuery(
    api.matches.listForUser,
    userId ? { userId, scene } : 'skip'
  );

  if (!userId) return null;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>匹配</Text>
      </View>

      <View style={styles.sceneRow}>
        {SCENES.map((s) => (
          <TouchableOpacity
            key={s.key}
            style={[styles.sceneTab, scene === s.key && { borderBottomColor: s.color, borderBottomWidth: 2 }]}
            onPress={() => setScene(s.key)}
          >
            <Text style={styles.sceneEmoji}>{s.emoji}</Text>
            <Text style={[styles.sceneLabel, scene === s.key && { color: s.color, fontWeight: '700' }]}>
              {s.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
        {matches === undefined && (
          <Text style={styles.empty}>加载中…</Text>
        )}
        {matches?.length === 0 && (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyEmoji}>🔍</Text>
            <Text style={styles.emptyTitle}>暂无匹配结果</Text>
            <Text style={styles.emptyDesc}>完善画像后，AI 会帮你找到合适的同学</Text>
          </View>
        )}
        {matches?.map((item) => {
          const accentColor = SCENES.find(s => s.key === scene)?.color ?? Colors.primary;
          return (
            <TouchableOpacity
              key={item.match._id}
              style={styles.card}
              onPress={() => router.push(`/match/${item.match._id}`)}
              activeOpacity={0.8}
            >
              <View style={styles.cardTop}>
                <View style={[styles.avatar, { backgroundColor: accentColor + '20' }]}>
                  <Text style={[styles.avatarText, { color: accentColor }]}>
                    {item.other?.nickname?.[0] ?? '?'}
                  </Text>
                </View>
                <View style={styles.cardInfo}>
                  <Text style={styles.cardName}>{item.other?.nickname ?? '匿名用户'}</Text>
                  <Text style={styles.cardSchool}>{item.other?.school}</Text>
                </View>
                <View style={styles.scoreBox}>
                  <Text style={[styles.scoreNum, { color: accentColor }]}>
                    {item.match.fitScore}
                  </Text>
                  <Text style={styles.scoreSuffix}>分</Text>
                </View>
              </View>

              <View style={styles.scoreRow}>
                <ScoreBar score={item.match.fitScore} />
                <Text style={styles.scoreLabel}>{item.match.fitScore}% 匹配</Text>
              </View>

              {item.otherCardText ? (
                <Text style={styles.cardText} numberOfLines={2}>
                  {item.otherCardText}
                </Text>
              ) : null}

              {item.match.sharedTopics.length > 0 && (
                <View style={styles.tagRow}>
                  {item.match.sharedTopics.slice(0, 3).map((t) => (
                    <View key={t} style={[styles.chip, { backgroundColor: accentColor + '15' }]}>
                      <Text style={[styles.chipText, { color: accentColor }]}>{t}</Text>
                    </View>
                  ))}
                </View>
              )}

              <View style={styles.statusRow}>
                <Text style={styles.statusText}>
                  {item.match.aStatus === 'new' && item.match.bStatus === 'new'
                    ? '等待双方决定'
                    : item.match.aStatus === 'interested' && item.match.bStatus === 'interested'
                    ? '🎉 双向心动'
                    : '查看详情 →'}
                </Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.sm },
  title: { fontSize: 28, fontWeight: '800', color: Colors.text },
  sceneRow: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: Colors.border },
  sceneTab: { flex: 1, alignItems: 'center', paddingVertical: Spacing.md, gap: 2 },
  sceneEmoji: { fontSize: 18 },
  sceneLabel: { fontSize: 13, color: Colors.textSecondary },
  list: { padding: Spacing.lg, gap: Spacing.md },
  empty: { textAlign: 'center', color: Colors.textMuted, marginTop: Spacing.xxl },
  emptyBox: { alignItems: 'center', marginTop: Spacing.xxl, gap: Spacing.sm },
  emptyEmoji: { fontSize: 48 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: Colors.text },
  emptyDesc: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center' },
  card: {
    backgroundColor: Colors.card,
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    gap: Spacing.sm,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  avatar: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: 20, fontWeight: '700' },
  cardInfo: { flex: 1 },
  cardName: { fontSize: 16, fontWeight: '700', color: Colors.text },
  cardSchool: { fontSize: 13, color: Colors.textSecondary },
  scoreBox: { flexDirection: 'row', alignItems: 'baseline', gap: 2 },
  scoreNum: { fontSize: 24, fontWeight: '800' },
  scoreSuffix: { fontSize: 13, color: Colors.textMuted },
  scoreRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  scoreLabel: { fontSize: 12, color: Colors.textMuted, width: 60 },
  cardText: { fontSize: 13, color: Colors.textSecondary, lineHeight: 18 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  chip: { paddingHorizontal: Spacing.sm, paddingVertical: 3, borderRadius: Radii.full },
  chipText: { fontSize: 12, fontWeight: '600' },
  statusRow: { borderTopWidth: 1, borderTopColor: Colors.border, paddingTop: Spacing.sm },
  statusText: { fontSize: 13, color: Colors.textMuted, textAlign: 'right' },
});
