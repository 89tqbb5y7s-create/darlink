import { useMutation, useQuery } from 'convex/react';
import { LinearGradient } from 'expo-linear-gradient';
import { useLocalSearchParams } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '../../convex/_generated/api';
import type { Id } from '../../convex/_generated/dataModel';
import { useAuth } from '@/src/lib/auth-context';
import { Colors, Radii, Spacing } from '@/constants/theme';
import { PressableScale } from '@/src/components/PressableScale';
import * as Haptics from 'expo-haptics';

function timeStr(ts: number) {
  return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

export default function ChatRoomScreen() {
  const { chatId } = useLocalSearchParams<{ chatId: string }>();
  const { auth } = useAuth();
  const userId = auth.status === 'authenticated' ? auth.userId : undefined;

  const messages = useQuery(api.chats.messages, chatId ? { chatId: chatId as Id<'chats'> } : 'skip');
  const sendMessage = useMutation(api.chats.sendMessage);

  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const listRef = useRef<FlatList>(null);

  useEffect(() => {
    if (messages?.length) setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 80);
  }, [messages?.length]);

  async function handleSend() {
    if (!chatId || !userId || !text.trim()) return;
    setError('');
    setSending(true);
    try {
      await sendMessage({ chatId: chatId as Id<'chats'>, senderId: userId, body: text.trim(), aiAssisted: false });
      setText('');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '发送失败');
    } finally { setSending(false); }
  }

  if (!userId) return null;

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={88}>
        {messages === undefined ? (
          <ActivityIndicator style={{ flex: 1 }} color={Colors.pinkDeep} />
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m._id}
            contentContainerStyle={styles.list}
            onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
            renderItem={({ item }) => {
              const isMine = item.senderId === userId;
              return (
                <View style={[styles.msgRow, isMine && styles.msgRowMine]}>
                  {isMine ? (
                    <LinearGradient
                      colors={[Colors.gradientStart, Colors.gradientEnd]}
                      start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
                      style={[styles.bubble, styles.bubbleMine]}
                    >
                      <Text style={styles.bubbleTextMine}>{item.body}</Text>
                      <View style={styles.bubbleMeta}>
                        {item.riskFlag === 'medium' && <Text style={{ fontSize: 10, color: 'rgba(255,255,255,0.7)' }}>⚠</Text>}
                        <Text style={styles.bubbleTimeMine}>{timeStr(item.createdAt)}</Text>
                      </View>
                    </LinearGradient>
                  ) : (
                    <View style={[styles.bubble, styles.bubbleOther]}>
                      <Text style={styles.bubbleTextOther}>{item.body}</Text>
                      <View style={styles.bubbleMeta}>
                        {item.riskFlag === 'medium' && <Text style={{ fontSize: 10, color: Colors.warning }}>⚠</Text>}
                        <Text style={styles.bubbleTimeOther}>{timeStr(item.createdAt)}</Text>
                        {item.aiAssisted && <Text style={styles.aiBadge}>AI</Text>}
                      </View>
                    </View>
                  )}
                </View>
              );
            }}
          />
        )}

        {error ? (
          <View style={styles.errorBar}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={text}
            onChangeText={setText}
            placeholder="自己输入内容…"
            placeholderTextColor={Colors.textPlaceholder}
            multiline
            maxLength={500}
          />
          <PressableScale
            style={styles.aiBtn}
            onPress={() => {}}
            haptic="light"
          >
            <Text style={styles.aiBtnText}>✦</Text>
          </PressableScale>
          <PressableScale
            onPress={handleSend}
            disabled={!text.trim() || sending}
            haptic="light"
          >
            <LinearGradient
              colors={text.trim() ? [Colors.gradientStart, Colors.gradientEnd] : [Colors.border, Colors.border]}
              start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
              style={styles.sendBtn}
            >
              {sending
                ? <ActivityIndicator color="#fff" size="small" />
                : <Text style={styles.sendIcon}>↑</Text>
              }
            </LinearGradient>
          </PressableScale>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  flex: { flex: 1 },
  list: { padding: Spacing.md, gap: 8, paddingBottom: Spacing.sm },
  msgRow: { flexDirection: 'row', justifyContent: 'flex-start' },
  msgRowMine: { justifyContent: 'flex-end' },
  bubble: { maxWidth: '78%', padding: Spacing.md, borderRadius: Radii.xl, gap: 4 },
  bubbleMine: { borderBottomRightRadius: 4 },
  bubbleOther: {
    backgroundColor: Colors.bgWhite,
    borderWidth: 1,
    borderColor: Colors.border,
    borderBottomLeftRadius: 4,
  },
  bubbleTextMine: { fontSize: 15, color: '#fff', lineHeight: 20 },
  bubbleTextOther: { fontSize: 15, color: Colors.text, lineHeight: 20 },
  bubbleMeta: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  bubbleTimeMine: { fontSize: 10, color: 'rgba(255,255,255,0.65)' },
  bubbleTimeOther: { fontSize: 10, color: Colors.textMuted },
  aiBadge: { fontSize: 10, color: Colors.study, fontWeight: '700' },
  errorBar: { backgroundColor: Colors.errorBg, padding: Spacing.sm, marginHorizontal: Spacing.md, borderRadius: Radii.md, marginBottom: 4 },
  errorText: { fontSize: 13, color: Colors.error, textAlign: 'center' },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Spacing.sm,
    padding: Spacing.md,
    paddingBottom: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.bgWhite,
  },
  input: {
    flex: 1,
    backgroundColor: Colors.bg,
    borderRadius: Radii.full,
    borderWidth: 1.5,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.md,
    paddingVertical: 10,
    fontSize: 15,
    color: Colors.text,
    maxHeight: 100,
  },
  aiBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: Colors.romanceBg,
    borderWidth: 1.5,
    borderColor: Colors.romanceBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  aiBtnText: { fontSize: 14, color: Colors.romance, fontWeight: '700' },
  sendBtn: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center' },
  sendIcon: { color: '#fff', fontSize: 18, fontWeight: '800' },
});
