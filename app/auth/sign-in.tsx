import { useMutation } from 'convex/react';
import { LinearGradient } from 'expo-linear-gradient';
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
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '../../convex/_generated/api';
import type { Id } from '../../convex/_generated/dataModel';
import { useAuth } from '@/src/lib/auth-context';
import { Colors, Radii, Shadows, Spacing } from '@/constants/theme';

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
    <SafeAreaView style={styles.container}>
      {/* Soft glow background orbs */}
      <View style={styles.orb1} pointerEvents="none" />
      <View style={styles.orb2} pointerEvents="none" />

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={styles.inner} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>

          {/* Logo */}
          <View style={styles.logoBlock}>
            <View style={styles.logoMark}>
              <View style={styles.logoCircleBlue} />
              <View style={styles.logoCirclePink} />
              <Text style={styles.logoStar}>✦</Text>
            </View>
            <Text style={styles.logoText}>
              滴搭 <Text style={styles.logoAccent}>Darlink</Text>
            </Text>
            <Text style={styles.tagline}>让你的 AI 分身，帮你找到真正合拍的人</Text>
          </View>

          {/* Badge */}
          <View style={styles.badge}>
            <Text style={styles.badgeText}>🛡️ 仅限真实大学生认证用户</Text>
          </View>

          {/* Form Card */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>创建你的账户</Text>

            <View style={styles.field}>
              <Text style={styles.label}>学校邮箱</Text>
              <TextInput
                style={styles.input}
                placeholder="xxx@university.edu.hk"
                placeholderTextColor={Colors.textPlaceholder}
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
                autoComplete="email"
              />
            </View>

            <View style={styles.field}>
              <Text style={styles.label}>昵称</Text>
              <TextInput
                style={styles.input}
                placeholder="让大家怎么称呼你？"
                placeholderTextColor={Colors.textPlaceholder}
                value={nickname}
                onChangeText={setNickname}
                maxLength={20}
              />
            </View>

            <View style={styles.field}>
              <Text style={styles.label}>学校</Text>
              <TouchableOpacity
                style={[styles.input, styles.select]}
                onPress={() => setShowSchools(!showSchools)}
              >
                <Text style={school ? styles.selectValue : styles.selectPlaceholder}>
                  {school || '选择你的学校'}
                </Text>
                <Text style={styles.chevron}>{showSchools ? '▲' : '▼'}</Text>
              </TouchableOpacity>
              {showSchools && (
                <View style={styles.dropdown}>
                  <ScrollView style={{ maxHeight: 200 }} nestedScrollEnabled>
                    {SCHOOLS.map((s) => (
                      <TouchableOpacity
                        key={s}
                        style={[styles.dropdownItem, school === s && styles.dropdownItemActive]}
                        onPress={() => { setSchool(s); setShowSchools(false); }}
                      >
                        <Text style={[styles.dropdownText, school === s && styles.dropdownTextActive]}>{s}</Text>
                      </TouchableOpacity>
                    ))}
                  </ScrollView>
                </View>
              )}
            </View>

            {error ? <Text style={styles.errorText}>{error}</Text> : null}

            {/* Gradient Button */}
            <TouchableOpacity
              onPress={handleSubmit}
              disabled={loading}
              style={styles.btnWrap}
              activeOpacity={0.85}
            >
              <LinearGradient
                colors={[Colors.gradientStart, Colors.gradientEnd]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={[styles.btn, loading && styles.btnDisabled]}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <Text style={styles.btnText}>生成我的 AI 分身</Text>
                    <Text style={styles.btnIcon}>✦</Text>
                  </>
                )}
              </LinearGradient>
            </TouchableOpacity>

            <Text style={styles.hint}>
              使用学校邮箱（.edu.hk / .edu.cn 等）自动通过认证
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const ORB_SIZE = 280;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  flex: { flex: 1 },
  orb1: {
    position: 'absolute',
    top: -60,
    left: -60,
    width: ORB_SIZE,
    height: ORB_SIZE,
    borderRadius: ORB_SIZE / 2,
    backgroundColor: Colors.pink,
    opacity: 0.12,
  },
  orb2: {
    position: 'absolute',
    bottom: 80,
    right: -80,
    width: ORB_SIZE + 60,
    height: ORB_SIZE + 60,
    borderRadius: (ORB_SIZE + 60) / 2,
    backgroundColor: Colors.blue,
    opacity: 0.10,
  },
  inner: { flexGrow: 1, justifyContent: 'center', padding: Spacing.lg, gap: Spacing.lg },
  logoBlock: { alignItems: 'center', gap: Spacing.sm },
  logoMark: { width: 56, height: 56, justifyContent: 'center', alignItems: 'center' },
  logoCircleBlue: {
    position: 'absolute',
    left: 4,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.blue,
    opacity: 0.6,
  },
  logoCirclePink: {
    position: 'absolute',
    right: 4,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.pink,
    opacity: 0.6,
  },
  logoStar: { position: 'absolute', fontSize: 14, color: '#fff', zIndex: 2, fontWeight: '700' },
  logoText: { fontSize: 28, fontWeight: '800', color: Colors.text, letterSpacing: 0.5 },
  logoAccent: { color: Colors.pinkDeep },
  tagline: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center' },
  badge: {
    alignSelf: 'center',
    backgroundColor: Colors.bgWhite,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radii.full,
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    ...Shadows.sm,
  },
  badgeText: { fontSize: 12, color: Colors.study, fontWeight: '600' },
  card: {
    backgroundColor: Colors.bgWhite,
    borderRadius: Radii['3xl'],
    padding: Spacing.lg,
    gap: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.md,
  },
  cardTitle: { fontSize: 20, fontWeight: '800', color: Colors.text, marginBottom: 4 },
  field: { gap: 6 },
  label: { fontSize: 13, fontWeight: '600', color: Colors.textBody },
  input: {
    backgroundColor: Colors.bg,
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: Radii.lg,
    padding: Spacing.md,
    fontSize: 15,
    color: Colors.text,
  },
  select: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  selectValue: { fontSize: 15, color: Colors.text },
  selectPlaceholder: { fontSize: 15, color: Colors.textPlaceholder },
  chevron: { fontSize: 11, color: Colors.textMuted },
  dropdown: {
    backgroundColor: Colors.bgWhite,
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: Radii.lg,
    overflow: 'hidden',
    ...Shadows.sm,
  },
  dropdownItem: { padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.borderLight },
  dropdownItemActive: { backgroundColor: Colors.studyBg },
  dropdownText: { fontSize: 15, color: Colors.textBody },
  dropdownTextActive: { color: Colors.study, fontWeight: '700' },
  errorText: { fontSize: 13, color: Colors.error },
  btnWrap: { marginTop: 4 },
  btn: {
    borderRadius: Radii.full,
    padding: Spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  btnIcon: { color: '#fff', fontSize: 16 },
  hint: { textAlign: 'center', color: Colors.textMuted, fontSize: 12, lineHeight: 18 },
});
