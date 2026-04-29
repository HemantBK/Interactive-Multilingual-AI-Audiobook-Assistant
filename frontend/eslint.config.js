// ESLint flat config (ESLint 9+).
//
// Day 24: minimal config — TS + React + react-hooks rules. Prettier is the
// formatter; eslint-config-prettier turns off any rules that would fight
// formatting. We disable prop-types (we use TS), and require-await (it's
// noisy on intentionally-async functions like SSE consumers).

import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import prettier from 'eslint-config-prettier';

export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**', 'playwright-report/**', 'test-results/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}'],
    plugins: {
      react,
      'react-hooks': reactHooks,
    },
    languageOptions: {
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        window: 'readonly',
        document: 'readonly',
        crypto: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        FormData: 'readonly',
        File: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        AbortController: 'readonly',
        ResizeObserver: 'readonly',
        TextDecoderStream: 'readonly',
        DOMException: 'readonly',
        MediaRecorder: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        HTMLElement: 'readonly',
        HTMLInputElement: 'readonly',
        HTMLTextAreaElement: 'readonly',
        HTMLAudioElement: 'readonly',
        HTMLDivElement: 'readonly',
        HTMLImageElement: 'readonly',
        HTMLFormElement: 'readonly',
        KeyboardEvent: 'readonly',
        Element: 'readonly',
        Blob: 'readonly',
        ReadableStream: 'readonly',
        RequestInit: 'readonly',
        Response: 'readonly',
      },
    },
    settings: { react: { version: 'detect' } },
    rules: {
      'react/jsx-uses-react': 'off',
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },
  // Test files: relax a few noisy rules
  {
    files: ['e2e/**/*.{ts,tsx}'],
    rules: {
      'no-console': 'off',
    },
  },
  prettier,
);
