import { useMutation } from 'convex/react';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import { api } from '../../convex/_generated/api';
import { useAuth } from '@/src/lib/auth-context';
import { Colors, Radii, Spacing } from '@/constants/theme';
import type { Id } from '../../convex/_generated/dataModel';

const SCHOOLS = [
  'HKU', 'CUHK', 'HKUST', 'PolyU', 'CityU', 'HKBU', 'LU', 'EdUHK',
  '北京大学', '清华大学', '复旦大学', '上海交通大学', '浙江大学', '南京大学', '武汉大学', '中山大学',
];

export default function SignInScreen() {
  const router = useRouter();
  const { signIn } = useAuth();
  const signInOrCreate = useMutation(api.auth.signInOrCreate);

  const [email, setEmail] = useState('');
  const [nickname, setNickname] = useState('');
  const [school, setSchool] = useState('');
  const [showSchools, setShowSchools] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit() {
    if (!email.trim() || !nickname.trim() || !school) {
      setError('请填写所有必填项');
      return;
    }
    if (!email.includes('@')) {
      setError('请输入有效的邮箱地址');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const userId = await signInOrCreate({ email: email.trim(), nickname: nickname.trim(), school });
      await signIn(userId as Id<'users'>);
      router.replace('/onboarding/questionnaire');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '登录失败，请重试');
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.inner} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text style={styles.logo}>滴搭</Text>
          <Text style={styles.tagline}>找到你的同频搭子</Text>
        </View>

        <View style={styles.form}>
          <Text style={styles.label}>学校邮箱</Text>
          <TextInput
            style={styles.input}
            placeholder="xxx@university.edu.hk"
            placeholderTextColor={Colors.textMuted}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            autoComplete="email"
          />

          <Text style={styles.label}>昵称</Text>
          <TextInput
            style={styles.input}
            placeholder="让大家怎么称呼你？"
            placeholderTextColor={Colors.textMuted}
            value={nickname}
            onChangeText={setNickname}
            maxLength={20}
          />

          <Text style={styles.label}>学校</Text>
          <TouchableOpacity
            style={[styles.input, styles.select]}
            onPress={() => setShowSchools(!showSchools)}
          >
            <Text style={school ? styles.selectText : styles.selectPlaceholder}>
              {school || '选择你的学校'}
            </Text>
            <Text style={styles.chevron}>{showSchools ? '▲' : '▼'}</Text>
          </TouchableOpacity>

          {showSchools && (
            <View style={styles.dropdown}>
              {SCHOOLS.map((s) => (
                <TouchableOpacity
                  key={s}
                  style={[styles.dropdownItem, school === s && styles.dropdownItemActive]}
                  onPress={() => {
                    setSchool(s);
                    setShowSchools(false);
                  }}
                >
                  <Text style={[styles.dropdownText, school === s && styles.dropdownTextActive]}>
                    {s}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={handleSubmit}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.btnText}>开始匹配之旅</Text>
            )}
          </TouchableOpacity>

          <Text style={styles.hint}>
            使用学校邮箱自动通过身份验证{'\n'}
            非学校邮箱需等待人工审核
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  inner: { flexGrow: 1, justifyContent: 'center', padding: Spacing.xl },
  header: { alignItems: 'center', marginBottom: Spacing.xxl },
  logo: { fontSize: 48, fontWeight: '800', color: Colors.primary, letterSpacing: -1 },
  tagline: { fontSize: 16, color: Colors.textSecondary, marginTop: Spacing.xs },
  form: { gap: Spacing.sm },
  label: { fontSize: 14, fontWeight: '600', color: Colors.text, marginTop: Spacing.sm },
  input: {
    backgroundColor: Colors.card,
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: Radii.md,
    padding: Spacing.md,
    fontSize: 15,
    color: Colors.text,
  },
  select: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  selectText: { fontSize: 15, color: Colors.text },
  selectPlaceholder: { fontSize: 15, color: Colors.textMuted },
  chevron: { fontSize: 12, color: Colors.textMuted },
  dropdown: {
    backgroundColor: Colors.card,
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: Radii.md,
    overflow: 'hidden',
    maxHeight: 200,
  },
  dropdownItem: {
    padding: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  dropdownItemActive: { backgroundColor: Colors.primaryLight + '20' },
  dropdownText: { fontSize: 15, color: Colors.text },
  dropdownTextActive: { color: Colors.primary, fontWeight: '600' },
  error: { color: Colors.error, fontSize: 13, marginTop: Spacing.xs },
  btn: {
    backgroundColor: Colors.primary,
    borderRadius: Radii.lg,
    padding: Spacing.md,
    alignItems: 'center',
    marginTop: Spacing.lg,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  hint: { textAlign: 'center', color: Colors.textMuted, fontSize: 12, marginTop: Spacing.md, lineHeight: 18 },
});
