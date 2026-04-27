import { useMutation } from 'convex/react';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
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

type Step = {
  key: string;
  question: string;
  type: 'single' | 'multi';
  options: { label: string; value: string }[];
  max?: number;
};

const STEPS: Step[] = [
  {
    key: 'socialGoal',
    question: '你来滴搭主要想找什么？',
    type: 'multi',
    max: 3,
    options: [
      { label: '学习搭子', value: '学习搭子' },
      { label: '饭搭子', value: '饭搭子' },
      { label: '运动搭子', value: '运动搭子' },
      { label: '聊天树洞', value: '聊天树洞' },
      { label: '恋爱对象', value: '恋爱对象' },
      { label: '新朋友', value: '新朋友' },
    ],
  },
  {
    key: 'socialEnergy',
    question: '你的社交能量是哪种？',
    type: 'single',
    options: [
      { label: '慢热型，熟了才深聊', value: 'introvert' },
      { label: '看场合，能内能外', value: 'ambivert' },
      { label: '主动型，愿意先破冰', value: 'extrovert' },
    ],
  },
  {
    key: 'communicationStyle',
    question: '你的聊天风格更接近哪种？',
    type: 'single',
    options: [
      { label: '简洁直接，不拐弯抹角', value: 'concise' },
      { label: '温和有回应，在乎对方感受', value: 'warm' },
      { label: '轻松幽默，喜欢玩梗', value: 'playful' },
      { label: '深思熟虑，把话讲清楚', value: 'thoughtful' },
    ],
  },
  {
    key: 'interests',
    question: '你最感兴趣的领域有哪些？（最多选5个）',
    type: 'multi',
    max: 5,
    options: [
      { label: '科技/编程', value: '科技/编程' },
      { label: '设计/艺术', value: '设计/艺术' },
      { label: '音乐', value: '音乐' },
      { label: '电影/剧集', value: '电影/剧集' },
      { label: '阅读', value: '阅读' },
      { label: '游戏', value: '游戏' },
      { label: '运动/健身', value: '运动/健身' },
      { label: '美食探店', value: '美食探店' },
      { label: '旅行', value: '旅行' },
      { label: '创业/商业', value: '创业/商业' },
      { label: '学术研究', value: '学术研究' },
      { label: '摄影', value: '摄影' },
    ],
  },
  {
    key: 'availability',
    question: '你通常什么时候有空？（可多选）',
    type: 'multi',
    options: [
      { label: '工作日上午', value: '工作日上午' },
      { label: '工作日下午', value: '工作日下午' },
      { label: '工作日晚上', value: '工作日晚上' },
      { label: '周末白天', value: '周末白天' },
      { label: '周末晚上', value: '周末晚上' },
    ],
  },
  {
    key: 'boundaries',
    question: '你的边界和偏好是什么？（可多选）',
    type: 'multi',
    options: [
      { label: '不太愿意视频通话', value: '不太愿意视频通话' },
      { label: '不喜欢突然打电话', value: '不喜欢突然打电话' },
      { label: '线上聊几天再见面', value: '线上聊几天再见面' },
      { label: '不讨论政治/宗教', value: '不讨论政治/宗教' },
      { label: '注重隐私，不分享定位', value: '注重隐私，不分享定位' },
      { label: '比较随和，没有特别限制', value: '比较随和，没有特别限制' },
    ],
  },
  {
    key: 'relationshipPace',
    question: '你希望关系发展的节奏是？',
    type: 'single',
    options: [
      { label: '慢一点，先聊够再见面', value: 'slow' },
      { label: '正常节奏，聊得来就约', value: 'medium' },
      { label: '快一些，有感觉就见', value: 'fast' },
    ],
  },
  {
    key: 'preferredScenes',
    question: '你喜欢在哪些场景认识新朋友？',
    type: 'multi',
    max: 3,
    options: [
      { label: '图书馆/自习室', value: '图书馆/自习室' },
      { label: '咖啡厅', value: '咖啡厅' },
      { label: '食堂', value: '食堂' },
      { label: '运动场所', value: '运动场所' },
      { label: '社团活动', value: '社团活动' },
      { label: '线上先聊', value: '线上先聊' },
    ],
  },
  {
    key: 'dislikeTopics',
    question: '哪些话题让你觉得不舒服？（可跳过）',
    type: 'multi',
    options: [
      { label: '家庭/父母', value: '家庭/父母' },
      { label: '感情史', value: '感情史' },
      { label: '成绩/GPA', value: '成绩/GPA' },
      { label: '薪资/钱', value: '薪资/钱' },
      { label: '政治', value: '政治' },
      { label: '宗教', value: '宗教' },
      { label: '没有特别忌讳', value: '没有特别忌讳' },
    ],
  },
  {
    key: 'values',
    question: '在关系中，你最看重什么？（最多选3个）',
    type: 'multi',
    max: 3,
    options: [
      { label: '真诚', value: '真诚' },
      { label: '幽默感', value: '幽默感' },
      { label: '共同兴趣', value: '共同兴趣' },
      { label: '互相尊重边界', value: '互相尊重边界' },
      { label: '有深度', value: '有深度' },
      { label: '轻松不累', value: '轻松不累' },
      { label: '上进心', value: '上进心' },
    ],
  },
];

type Answers = Record<string, string[]>;

export default function QuestionnaireScreen() {
  const router = useRouter();
  const { auth } = useAuth();
  const upsertQuestionnaire = useMutation(api.profile.upsertQuestionnaire);

  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [submitting, setSubmitting] = useState(false);

  const current = STEPS[step];
  const selected: string[] = answers[current.key] ?? [];

  function toggle(value: string) {
    const cur = answers[current.key] ?? [];
    if (current.type === 'single') {
      setAnswers({ ...answers, [current.key]: [value] });
    } else {
      if (cur.includes(value)) {
        setAnswers({ ...answers, [current.key]: cur.filter((v) => v !== value) });
      } else {
        if (current.max && cur.length >= current.max) return;
        setAnswers({ ...answers, [current.key]: [...cur, value] });
      }
    }
  }

  function canNext() {
    if (current.key === 'dislikeTopics') return true;
    return (answers[current.key] ?? []).length > 0;
  }

  async function handleNext() {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
      return;
    }
    if (auth.status !== 'authenticated') return;
    setSubmitting(true);
    try {
      await upsertQuestionnaire({
        userId: auth.userId,
        socialGoal: answers.socialGoal ?? [],
        socialEnergy: (answers.socialEnergy?.[0] ?? 'ambivert') as 'introvert' | 'ambivert' | 'extrovert',
        communicationStyle: (answers.communicationStyle?.[0] ?? 'warm') as 'concise' | 'warm' | 'playful' | 'thoughtful',
        interests: answers.interests ?? [],
        availability: answers.availability ?? [],
        boundaries: answers.boundaries ?? [],
        relationshipPace: (answers.relationshipPace?.[0] ?? 'medium') as 'slow' | 'medium' | 'fast',
        preferredScenes: answers.preferredScenes ?? [],
        dislikeTopics: answers.dislikeTopics ?? [],
        values: answers.values ?? [],
        raw: answers,
      });
      router.replace('/(tabs)');
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  }

  const progress = (step + 1) / STEPS.length;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.progressBar}>
        <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
      </View>

      <Text style={styles.stepCount}>
        {step + 1} / {STEPS.length}
      </Text>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.question}>{current.question}</Text>
        {current.max && (
          <Text style={styles.maxHint}>最多选 {current.max} 个</Text>
        )}

        <View style={styles.options}>
          {current.options.map((opt) => {
            const isSelected = selected.includes(opt.value);
            return (
              <TouchableOpacity
                key={opt.value}
                style={[styles.option, isSelected && styles.optionSelected]}
                onPress={() => toggle(opt.value)}
                activeOpacity={0.7}
              >
                <Text style={[styles.optionText, isSelected && styles.optionTextSelected]}>
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </ScrollView>

      <View style={styles.footer}>
        {step > 0 && (
          <TouchableOpacity style={styles.backBtn} onPress={() => setStep(step - 1)}>
            <Text style={styles.backText}>上一题</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          style={[styles.nextBtn, (!canNext() || submitting) && styles.nextBtnDisabled]}
          onPress={handleNext}
          disabled={!canNext() || submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.nextText}>
              {step < STEPS.length - 1 ? '下一题' : '生成我的数字人'}
            </Text>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  progressBar: { height: 4, backgroundColor: Colors.border, marginHorizontal: 0 },
  progressFill: { height: 4, backgroundColor: Colors.primary, borderRadius: 2 },
  stepCount: {
    textAlign: 'right',
    fontSize: 13,
    color: Colors.textMuted,
    padding: Spacing.md,
    paddingBottom: 0,
  },
  content: { padding: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.xxl },
  question: {
    fontSize: 22,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: Spacing.xs,
    lineHeight: 30,
  },
  maxHint: { fontSize: 13, color: Colors.textMuted, marginBottom: Spacing.md },
  options: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm, marginTop: Spacing.md },
  option: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radii.full,
    borderWidth: 1.5,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
  },
  optionSelected: { borderColor: Colors.primary, backgroundColor: Colors.primary + '15' },
  optionText: { fontSize: 14, color: Colors.textSecondary },
  optionTextSelected: { color: Colors.primary, fontWeight: '600' },
  footer: {
    flexDirection: 'row',
    gap: Spacing.sm,
    padding: Spacing.lg,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.bg,
  },
  backBtn: {
    flex: 1,
    padding: Spacing.md,
    borderRadius: Radii.lg,
    borderWidth: 1.5,
    borderColor: Colors.border,
    alignItems: 'center',
  },
  backText: { fontSize: 15, color: Colors.textSecondary, fontWeight: '600' },
  nextBtn: {
    flex: 2,
    padding: Spacing.md,
    borderRadius: Radii.lg,
    backgroundColor: Colors.primary,
    alignItems: 'center',
  },
  nextBtnDisabled: { opacity: 0.4 },
  nextText: { fontSize: 15, color: '#fff', fontWeight: '700' },
});
