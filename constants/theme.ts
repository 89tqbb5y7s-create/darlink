import { Platform } from 'react-native';

export const Colors = {
  primary: '#7C5CFC',
  primaryLight: '#A78BFA',
  primaryDark: '#5B3FE0',

  study: '#4ECDC4',
  food: '#FF9F43',
  romance: '#FF6B81',

  bg: '#F8F9FE',
  card: '#FFFFFF',
  border: '#E8E8F0',

  text: '#1A1A2E',
  textSecondary: '#64648A',
  textMuted: '#A0A0C0',

  success: '#2ECC71',
  warning: '#F1C40F',
  error: '#E74C3C',

  light: {
    text: '#1A1A2E',
    background: '#F8F9FE',
    tint: '#7C5CFC',
    icon: '#64648A',
    tabIconDefault: '#A0A0C0',
    tabIconSelected: '#7C5CFC',
  },
  dark: {
    text: '#F0F0FF',
    background: '#0F0F1E',
    tint: '#A78BFA',
    icon: '#9090B0',
    tabIconDefault: '#6060A0',
    tabIconSelected: '#A78BFA',
  },
};

export const Fonts = Platform.select({
  ios: {
    sans: 'system-ui',
    serif: 'ui-serif',
    rounded: 'ui-rounded',
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    serif: "Georgia, 'Times New Roman', serif",
    rounded: "'SF Pro Rounded', sans-serif",
    mono: "SFMono-Regular, Menlo, Monaco, Consolas, 'Courier New', monospace",
  },
});

export const Radii = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 9999,
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};
