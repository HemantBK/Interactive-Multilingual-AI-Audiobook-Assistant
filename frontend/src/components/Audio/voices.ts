/**
 * Frontend mirror of backend's voices catalog.
 *
 * For Day 16 we hardcode this so the chat UI can pick a default without a
 * /voices round trip on every render. Day 19 polish wires the voice picker
 * UI to load /voices once on auth and cache in memory.
 */

export interface VoiceOption {
  voice_id: string;
  language: string;
  label: string;
  gender: 'female' | 'male';
}

export const VOICE_OPTIONS: readonly VoiceOption[] = [
  { voice_id: 'en-female', language: 'en', label: 'English — Aria', gender: 'female' },
  { voice_id: 'en-male',   language: 'en', label: 'English — Guy',  gender: 'male' },
  { voice_id: 'hi-female', language: 'hi', label: 'हिन्दी — स्वरा', gender: 'female' },
  { voice_id: 'hi-male',   language: 'hi', label: 'हिन्दी — मधुर', gender: 'male' },
  { voice_id: 'ta-female', language: 'ta', label: 'தமிழ் — பல்லவி', gender: 'female' },
  { voice_id: 'ta-male',   language: 'ta', label: 'தமிழ் — வள்ளுவர்', gender: 'male' },
  { voice_id: 'bn-female', language: 'bn', label: 'বাংলা — তানিশা', gender: 'female' },
  { voice_id: 'bn-male',   language: 'bn', label: 'বাংলা — ভাস্কর', gender: 'male' },
  { voice_id: 'mr-female', language: 'mr', label: 'मराठी — आरोही', gender: 'female' },
  { voice_id: 'mr-male',   language: 'mr', label: 'मराठी — मनोहर', gender: 'male' },
  { voice_id: 'te-female', language: 'te', label: 'తెలుగు — శ్రుతి', gender: 'female' },
  { voice_id: 'te-male',   language: 'te', label: 'తెలుగు — మోహన్', gender: 'male' },
];

/** Pick the female voice for a language code, English fallback. */
export function defaultVoiceIdForLanguage(language: string | null): string {
  if (language) {
    const match = VOICE_OPTIONS.find(
      (v) => v.language === language && v.gender === 'female',
    );
    if (match) return match.voice_id;
  }
  return 'en-female';
}
