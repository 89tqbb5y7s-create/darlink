import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const upsertQuestionnaire = mutation({
  args: {
    userId: v.id("users"),
    socialGoal: v.array(v.string()),
    socialEnergy: v.union(
      v.literal("introvert"),
      v.literal("ambivert"),
      v.literal("extrovert"),
    ),
    communicationStyle: v.union(
      v.literal("concise"),
      v.literal("warm"),
      v.literal("playful"),
      v.literal("thoughtful"),
    ),
    interests: v.array(v.string()),
    availability: v.array(v.string()),
    boundaries: v.array(v.string()),
    relationshipPace: v.union(
      v.literal("slow"),
      v.literal("medium"),
      v.literal("fast"),
    ),
    preferredScenes: v.array(v.string()),
    dislikeTopics: v.array(v.string()),
    values: v.array(v.string()),
    raw: v.any(),
  },
  handler: async (ctx, args) => {
    const { userId, raw, ...rest } = args;
    const existing = await ctx.db
      .query("studentProfiles")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .unique();

    const payload = {
      userId,
      ...rest,
      questionnaireAnswers: raw,
      updatedAt: Date.now(),
    };

    if (existing) {
      await ctx.db.patch(existing._id, payload);
      return existing._id;
    }
    return await ctx.db.insert("studentProfiles", payload);
  },
});

export const getProfile = query({
  args: { userId: v.id("users") },
  handler: async (ctx, { userId }) => {
    return await ctx.db
      .query("studentProfiles")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .unique();
  },
});

export const getDigitalHuman = query({
  args: { userId: v.id("users") },
  handler: async (ctx, { userId }) => {
    return await ctx.db
      .query("digitalHumans")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .unique();
  },
});

export const saveDigitalHuman = mutation({
  args: {
    userId: v.id("users"),
    cardText: v.string(),
    skillMd: v.string(),
    mentalModels: v.array(v.string()),
    decisionHeuristics: v.array(v.string()),
    expressionPatterns: v.array(v.string()),
    publicFields: v.array(v.string()),
    privateFields: v.array(v.string()),
  },
  handler: async (ctx, args) => {
    const { userId, ...rest } = args;
    const existing = await ctx.db
      .query("digitalHumans")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .unique();

    if (existing) {
      await ctx.db.patch(existing._id, {
        ...rest,
        version: existing.version + 1,
        updatedAt: Date.now(),
      });
      return existing._id;
    }

    return await ctx.db.insert("digitalHumans", {
      userId,
      ...rest,
      version: 1,
      updatedAt: Date.now(),
    });
  },
});

export const resetDigitalHuman = mutation({
  args: { userId: v.id("users") },
  handler: async (ctx, { userId }) => {
    const existing = await ctx.db
      .query("digitalHumans")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .unique();
    if (existing) await ctx.db.delete(existing._id);
  },
});
