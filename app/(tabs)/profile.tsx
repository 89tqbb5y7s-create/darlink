import { useQuery } from 'convex/react';
import { useRouter } from 'expo-router';
import React from 'react';
import {
  Alert,
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

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value ?? '—'}</Text>
    </View>
  );
}

export default function ProfileScreen() {
  const router = useRouter();
  const { auth, signOut } = useAuth();
  const userId = auth.status === 'authenticated' ? auth.userId : undefined;

  const user = useQuery(api.auth.me, userId ? { userId } : 'skip');
  const profile = useQuery(api.profile.getProfile, userId ? { userId } : 'skip');

  function handleSignOut() {
    Alert.alert('退出登录', '确定要退出吗？', [
      { text: '取消', style: 'cancel' },
      {
        text: '退出',
        style: 'destructive',
        onPress: () => signOut(),
      },
    ]);
  }

  if (!userId) return null;

  const energyMap: Record<string, string> = {
    introvert: '慢热型',
    ambivert: '随机应变',
    extrovert: '主动型',
  };
  const styleMap: Record<string, string> = {
    concise: '简洁直接',
    warm: '温和有回应',
    playful: '轻松幽默',
    thoughtful: '深思熟虑',
  };
  const paceMap: Record<string, string> = {
    slow: '慢慢来',
    medium: '正常节奏',
    fast: '快节奏',
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View style={styles.avatarLarge}>
            <Text style={styles.avatarText}>{user?.nickname?.[0] ?? '?'}</Text>
          </View>
          <Text style={styles.nickname}>{user?.nickname}</Text>
          <Text style={styles.school}>{user?.school}</Text>
          <View style={[
            styles.badge,
            { backgroundColor: user?.verifiedStatus === 'verified' ? Colors.success + '20' : Colors.warning + '20' }
          ]}>
            <Text style={{ fontSize: 12, color: user?.verifiedStatus === 'verified' ? Colors.success : Colors.warning, fontWeight: '600' }}>
              {user?.verifiedStatus === 'verified' ? '✓ 已认证' : '待认证'}
            </Text>
          </View>
        </View>

        {profile ? (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>我的画像</Text>
              <TouchableOpacity onPress={() => router.push('/onboarding/questionnaire')}>
                <Text style={styles.editLink}>重新填写</Text>
              </TouchableOpacity>
            </View>
            <Row label="社交能量" value={energyMap[profile.socialEnergy]} />
            <Row label="聊天风格" value={styleMap[profile.communicationStyle]} />
            <Row label="关系节奏" value={paceMap[profile.relationshipPace]} />
            <Row label="兴趣" value={profile.interests.slice(0, 3).join(' · ')} />
            <Row label="目标" value={profile.socialGoal.join(' · ')} />
          </View>
        ) : (
          <TouchableOpacity
            style={styles.ctaCard}
            onPress={() => router.push('/onboarding/questionnaire')}
          >
            <Text style={styles.ctaText}>📝 填写画像问卷，开始匹配</Text>
          </TouchableOpacity>
        )}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>账户信息</Text>
          <Row label="邮箱" value={user?.email} />
          <Row label="专业" value={user?.major} />
          <Row label="年级" value={user?.grade} />
        </View>

        <TouchableOpacity style={styles.signOutBtn} onPress={handleSignOut}>
          <Text style={styles.signOutText}>退出登录</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  content: { padding: Spacing.lg, gap: Spacing.lg },
  header: { alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.lg },
  avatarLarge: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.primary + '20',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { fontSize: 32, fontWeight: '700', color: Colors.primary },
  nickname: { fontSize: 24, fontWeight: '800', color: Colors.text },
  school: { fontSize: 14, color: Colors.textSecondary },
  badge: { paddingHorizontal: Spacing.md, paddingVertical: 4, borderRadius: Radii.full },
  card: {
    backgroundColor: Colors.card,
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    gap: Spacing.sm,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: Spacing.xs },
  cardTitle: { fontSize: 16, fontWeight: '700', color: Colors.text },
  editLink: { fontSize: 14, color: Colors.primary, fontWeight: '600' },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: Colors.border },
  rowLabel: { fontSize: 14, color: Colors.textSecondary },
  rowValue: { fontSize: 14, color: Colors.text, fontWeight: '500', maxWidth: '60%', textAlign: 'right' },
  ctaCard: {
    backgroundColor: Colors.primary + '10',
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    borderWidth: 1.5,
    borderColor: Colors.primary + '40',
    borderStyle: 'dashed',
    alignItems: 'center',
  },
  ctaText: { fontSize: 15, color: Colors.primary, fontWeight: '600' },
  signOutBtn: {
    borderRadius: Radii.lg,
    padding: Spacing.md,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: Colors.error + '60',
  },
  signOutText: { color: Colors.error, fontSize: 15, fontWeight: '600' },
});
