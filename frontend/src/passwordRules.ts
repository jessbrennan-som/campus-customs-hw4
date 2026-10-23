// The same password rules the backend enforces (backend/security.py). The checklist on the sign-up
// page ticks them off as you type; the server still checks them again, so they can't be skipped.

export const MIN_LENGTH = 10
export const MAX_LENGTH = 64

export type Who = { email?: string; first?: string; last?: string }
export type Rule = { id: string; label: string; ok: (password: string, who: Who) => boolean }

const COMMON = ['password', 'passw0rd', 'qwerty', 'letmein', 'welcome', 'iloveyou', 'admin', 'abc123', '123456', '111111', '000000']

export const RULES: Rule[] = [
  { id: 'length', label: `${MIN_LENGTH} to ${MAX_LENGTH} characters`, ok: (p) => p.length >= MIN_LENGTH && p.length <= MAX_LENGTH },
  { id: 'lower', label: 'a lowercase letter', ok: (p) => /[a-z]/.test(p) },
  { id: 'upper', label: 'an uppercase letter', ok: (p) => /[A-Z]/.test(p) },
  { id: 'digit', label: 'a number', ok: (p) => /\d/.test(p) },
  { id: 'special', label: 'a symbol, like ! ? # $ %', ok: (p) => /[^A-Za-z0-9\s]/.test(p) },
  {
    id: 'not_common',
    label: 'nothing easy to guess, like “password” or “123456”',
    ok: (p) => !COMMON.some((c) => p.toLowerCase().includes(c)) && !/(.)\1{3,}/.test(p),
  },
  {
    id: 'not_personal',
    label: 'no part of your name or email',
    ok: (p, w) => {
      const low = p.toLowerCase()
      return ![(w.email ?? '').split('@')[0], w.first ?? '', w.last ?? ''].some((x) => x.trim().length >= 3 && low.includes(x.trim().toLowerCase()))
    },
  },
]

export const brokenRules = (password: string, who: Who = {}) => RULES.filter((r) => !r.ok(password, who))
