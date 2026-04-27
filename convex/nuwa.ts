"use node";

import { action } from "./_generated/server";
import { api } from "./_generated/api";
import { v } from "convex/values";
import { distillDeterministic, DISTILL_LLM_PROMPT, type Profile } from "./lib/distill";

export const distillForUser = action({
  args: { userId: v.id("users") },
  handler: async (ctx, { userId }): Promise<{ status: "saved"; mode: "llm" | "deterministic" }> => {
    const profile = await ctx.runQuery(api.profile.getProfile, { userId });
    if (!profile) throw new Error("画像问卷尚未提交");

    const profileShape: Profile = {
      socialGoal: profile.socialGoal,
      socialEnergy: profile.socialEnergy,
      communicationStyle: profile.communicationStyle,
      interests: profile.interests,
      availability: profile.availability,
      boundaries: profile.boundaries,
      relationshipPace: profile.relationshipPace,
      preferredScenes: profile.preferredScenes,
      dislikeTopics: profile.dislikeTopics,
      values: profile.values,
    };

    const baseline = distillDeterministic(profileShape);

    const apiKey = process.env.OPENAI_API_KEY;
    let enhanced = baseline;
    let mode: "llm" | "deterministic" = "deterministic";

    if (apiKey) {
      try {
        const llm = await callOpenAI(apiKey, profileShape);
        if (llm) {
          enhanced = {
            ...baseline,
            cardText: llm.cardText || baseline.cardText,
            mentalModels: llm.mentalModels?.length ? llm.mentalModels : baseline.mentalModels,
            decisionHeuristics: llm.decisionHeuristics?.length
              ? llm.decisionHeuristics
              : baseline.decisionHeuristics,
            expressionPatterns: llm.expressionPatterns?.length
              ? llm.expressionPatterns
              : baseline.expressionPatterns,
          };
          mode = "llm";
        }
      } catch (err) {
        console.error("LLM enhancement failed, falling back to deterministic:", err);
      }
    }

    await ctx.runMutation(api.profile.saveDigitalHuman, {
      userId,
      ...enhanced,
    });

    return { status: "saved", mode };
  },
});

async function callOpenAI(apiKey: string, profile: Profile) {
  const prompt = DISTILL_LLM_PROMPT.replace(
    "{{PROFILE_JSON}}",
    JSON.stringify(profile, null, 2),
  );

  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: prompt }],
      response_format: { type: "json_object" },
      temperature: 0.7,
    }),
  });

  if (!res.ok) throw new Error(`OpenAI ${res.status}`);
  const data = (await res.json()) as { choices?: { message?: { content?: string } }[] };
  const raw = data.choices?.[0]?.message?.content;
  if (!raw) return null;

  return JSON.parse(raw) as {
    cardText?: string;
    mentalModels?: string[];
    decisionHeuristics?: string[];
    expressionPatterns?: string[];
  };
}
