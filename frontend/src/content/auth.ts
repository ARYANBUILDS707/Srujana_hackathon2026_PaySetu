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
      "signed-out-everywhere": "You have signed out on every device. Sign in again to continue.",
      "password-reset":
        "Your password has been reset and every device was signed out. Sign in with your new password.",
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
  forgot: {
    title: "Reset your password",
    intro:
      "Enter the email you use for PaySetu. If it has an account, we will send a link to choose a new password.",
    submit: "Send reset link",
    doneTitle: "Check your email",
    back: "Back to sign in",
    linkFromLogin: "Forgot password?",
  },
  reset: {
    title: "Choose a new password",
    intro: "Every device signed in to your account will be signed out.",
    submit: "Set new password",
    confirmLabel: "Confirm new password",
    mismatch: "The passwords do not match.",
    checking: "Checking your reset link",
    missingTitle: "This reset link is incomplete",
    missingBody: "Open the link from the email again, or request a new one.",
    invalidTitle: "This reset link can no longer be used",
    invalidBody:
      "Reset links work once and expire after 15 minutes. Request a new one to continue.",
    requestNew: "Request a new link",
    doneTitle: "Password reset",
    doneBody: "Your password has been changed and every device was signed out.",
    noticeSent: "We sent a confirmation to your email address.",
    noticeFailed: "We could not send the confirmation email, but your password has been changed.",
    signIn: "Sign in",
  },
  settings: {
    title: "Account settings",
    description: "Your sign-in details and active sessions.",
    accountTitle: "Account",
    changeTitle: "Change password",
    changeDescription: "You stay signed in here; every other device is signed out.",
    current: "Current password",
    next: "New password",
    confirm: "Confirm new password",
    submit: "Change password",
    doneTitle: "Password changed",
    doneBody: "Every other device has been signed out.",
    noticeSent: "A confirmation email has been sent to",
    noticeFailed: "We could not send the confirmation email. Your password has still been changed.",
    everywhereTitle: "Sign out everywhere",
    everywhereDescription:
      "Ends every session on every device, including this one. Use it if you signed in on a shared or lost device.",
    everywhereButton: "Sign out everywhere",
    everywhereConfirm: "Yes, sign out on every device",
    cancel: "Cancel",
  },
  fallbackError: "Something went wrong. Please try again.",
};
