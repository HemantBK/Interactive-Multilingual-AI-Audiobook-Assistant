export enum AppState {
  UPLOAD = 'UPLOAD',
  PROCESSING = 'PROCESSING',
  INTERACTIVE = 'INTERACTIVE'
}

export interface DocumentChunk {
  id: string;
  text: string;
  embedding?: number[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: number;
}

export interface VoiceOption {
  name: string;
  label: string;
  gender: 'Male' | 'Female';
}

export const AVAILABLE_VOICES: VoiceOption[] = [
  { name: 'Puck', label: 'Puck (Male)', gender: 'Male' },
  { name: 'Charon', label: 'Charon (Male)', gender: 'Male' },
  { name: 'Kore', label: 'Kore (Female)', gender: 'Female' },
  { name: 'Fenrir', label: 'Fenrir (Male)', gender: 'Male' },
  { name: 'Zephyr', label: 'Zephyr (Female)', gender: 'Female' },
];

export enum Language {
  ENGLISH = 'English',
  SPANISH = 'Spanish',
  FRENCH = 'French',
  GERMAN = 'German',
  JAPANESE = 'Japanese',
  CHINESE = 'Chinese',
  PORTUGUESE = 'Portuguese',
  ITALIAN = 'Italian',
  RUSSIAN = 'Russian',
  HINDI = 'Hindi',
  BENGALI = 'Bengali',
  MARATHI = 'Marathi',
  TAMIL = 'Tamil',
  TELUGU = 'Telugu'
}