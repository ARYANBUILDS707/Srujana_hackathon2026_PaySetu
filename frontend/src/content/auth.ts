// UI copy for sign-in and sign-up (DESIGN.md Section 13: plain language, honest labels).

export const authCopy = {
  login: {
    title: "Sign in",
    intro: "Sign in to your PaySetu workspace.",
    submit: "Sign in",
    switchPrompt: "New to PaySetu?",
    switchLink: "Create an account",
    reasons: {
      expired: "Your session has ended. Sign in again to continue.",
      "signed-out": "You have signed out.",
    } as Record<string, string>,
  },
  signup: {
    title: "Create an account",
    intro: "One account per business. You can record deliveries as soon as it is created.",
    submit: "Create account",
    switchPrompt: "Already have an account?",
    switchLink: "Sign in",
    passwordHint: "At least 10 characters. Very common passwords are refused.",
    businessHint: "The supplier name used on your cases and evidence packs.",
    // Accepted as `accept_terms_version` (backend CURRENT_TERMS_VERSION).
    termsVersion: "evaluation-2026-10",
    termsLabel:
      "I understand this is an evaluation build: PaySetu prepares evidence, it is not legal advice, and I will not enter real business or personal data.",
  },
  fallbackError: "Something went wrong. Please try again.",
};
