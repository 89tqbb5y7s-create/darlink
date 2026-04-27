import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Colors, Spacing } from '@/constants/theme';

export default function ActivityScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>活动</Text>
      </View>
      <View style={styles.center}>
        <Text style={styles.emoji}>🎉</Text>
        <Text style={styles.label}>活动功能即将上线</Text>
        <Text style={styles.desc}>校内活动、兴趣组队，敬请期待</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.sm },
  title: { fontSize: 28, fontWeight: '800', color: Colors.text },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 8 },
  emoji: { fontSize: 56 },
  label: { fontSize: 18, fontWeight: '700', color: Colors.text },
  desc: { fontSize: 14, color: Colors.textSecondary },
});
