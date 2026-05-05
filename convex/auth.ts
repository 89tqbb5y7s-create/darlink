import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const APPROVED_DOMAINS = [
  "edu",
  "edu.cn",
  "edu.hk",
  "edu.mo",
  "edu.tw",
  "ac.cn",
  "ac.hk",
];

function isStudentEmail(email: string) {
  const lower = email.toLowerCase().trim();
  return APPROVED_DOMAINS.some((d) => lower.endsWith(`.${d}`));
}

export const signInOrCreate = mutation({
  args: {
    email: v.string(),
    nickname: v.string(),
    school: v.string(),
  },
  handler: async (ctx, { email, nickname, school }) => {
    const lower = email.toLowerCase().trim();
    if (!lower.includes("@")) throw new Error("邮箱格式不正确");

    const existing = await ctx.db
      .query("users")
      .withIndex("by_email", (q) => q.eq("email", lower))
      .unique();

    if (existing) return existing._id;

    const verified = isStudentEmail(lower);
    return await ctx.db.insert("users", {
      email: lower,
      nickname,
      school,
      verifiedStatus: verified ? "verified" : "pending",
      verifiedVia: verified ? "email" : undefined,
      createdAt: Date.now(),
    });
  },
});

export const me = query({
  args: { userId: v.id("users") },
  handler: async (ctx, { userId }) => {
    return await ctx.db.get(userId);
  },
});

export const updateBasic = mutation({
  args: {
    userId: v.id("users"),
    nickname: v.optional(v.string()),
    avatarUrl: v.optional(v.string()),
    major: v.optional(v.string()),
    grade: v.optional(v.string()),
    selfPersonality: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const { userId, ...patch } = args;
    const cleaned: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(patch)) {
      if (v !== undefined) cleaned[k] = v;
    }
    await ctx.db.patch(userId, cleaned);
  },
});
