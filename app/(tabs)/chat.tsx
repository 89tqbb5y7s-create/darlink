import { useQuery } from 'convex/react';
import { useRouter } from 'expo-router';
import React from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '../../convex/_generated/api';
import { useAuth } from '@/src/lib/auth-context';
import { Colors, Radii, Spacing } from '@/constants/theme';

function timeAgo(ts: number) {
  const diff = Date.now() - ts;
  if (diff < 60_000) return '刚刚';
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}分钟前`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}小时前`;
  return `${Math.floor(diff / 86_400_000)}天前`;
}

export default function ChatScreen() {
  const router = useRouter();
  const { auth } = useAuth();
  const userId = auth.status === 'authenticated' ? auth.userId : undefined;

  const chats = useQuery(api.chats.listForUser, userId ? { userId } : 'skip');

  if (!userId) return null;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>聊天</Text>
      </View>

      <ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
        {chats === undefined && (
          <Text style={styles.empty}>加载中…</Text>
        )}
        {chats?.length === 0 && (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyEmoji}>💬</Text>
            <Text style={styles.emptyTitle}>暂无聊天</Text>
            <Text style={styles.emptyDesc}>双向心动后，聊天窗口会在这里出现</Text>
          </View>
        )}
        {chats?.map((item) => (
          <TouchableOpacity
            key={item.chat._id}
            style={styles.row}
            onPress={() => router.push(`/chat/${item.chat._id}`)}
            activeOpacity={0.7}
          >
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {item.other?.nickname?.[0] ?? '?'}
              </Text>
            </View>
            <View style={styles.info}>
              <View style={styles.topRow}>
                <Text style={styles.name}>{item.other?.nickname ?? '匿名用户'}</Text>
                {item.lastMessage && (
                  <Text style={styles.time}>{timeAgo(item.lastMessage.createdAt)}</Text>
                )}
              </View>
              <Text style={styles.preview} numberOfLines={1}>
                {item.lastMessage?.body ?? '还没有消息，说个你好吧～'}
              </Text>
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.sm },
  title: { fontSize: 28, fontWeight: '800', color: Colors.text },
  list: { paddingVertical: Spacing.sm },
  empty: { textAlign: 'center', color: Colors.textMuted, marginTop: Spacing.xxl },
  emptyBox: { alignItems: 'center', marginTop: Spacing.xxl, gap: Spacing.sm, padding: Spacing.lg },
  emptyEmoji: { fontSize: 48 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: Colors.text },
  emptyDesc: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center' },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    backgroundColor: Colors.card,
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: Colors.primary + '20',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { fontSize: 20, fontWeight: '700', color: Colors.primary },
  info: { flex: 1 },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 3 },
  name: { fontSize: 16, fontWeight: '700', color: Colors.text },
  time: { fontSize: 12, color: Colors.textMuted },
  preview: { fontSize: 14, color: Colors.textSecondary },
});
