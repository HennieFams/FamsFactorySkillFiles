import { definePreset } from '@primeuix/themes';
import Lara from '@primeuix/themes/lara';
import { FAMS, orangeScale, deepOrangeScale, amberScale, steelScale, darkSurfaceScale } from './palette';

// fams-ui-standards §1-2. Primary = FAMS orange, surfaces = FAMS greys.
// PrimeVue severities read primitive colour names (red = danger, orange = warn,
// green = success, sky = info ...). We remap those primitives to palette scales so
// every built-in component (Tag, Message, Toast, Button, Badge ...) stays on-palette:
//   danger  -> orange-deep   (critical)
//   warn    -> amber         (warning / exception)
//   info    -> FAMS orange   (active / live)
//   success -> steel grey    (healthy / normal - neutral on purpose)
const remapped = {
  red: deepOrangeScale,
  rose: deepOrangeScale,
  orange: amberScale,
  amber: amberScale,
  yellow: amberScale,
  sky: orangeScale,
  blue: orangeScale,
  indigo: orangeScale,
  cyan: orangeScale,
  green: steelScale,
  emerald: steelScale,
  teal: steelScale,
  lime: steelScale,
  purple: steelScale,
  violet: steelScale,
  fuchsia: steelScale,
  pink: steelScale,
  slate: steelScale,
  gray: steelScale,
  zinc: steelScale,
  neutral: steelScale,
  stone: steelScale
};

export const FamsPreset = definePreset(Lara, {
  primitive: remapped,
  semantic: {
    primary: orangeScale,
    focusRing: { width: '2px', style: 'solid', color: FAMS.orange, offset: '1px' },
    colorScheme: {
      light: {
        surface: steelScale,
        primary: {
          color: FAMS.orange,
          contrastColor: FAMS.white,
          hoverColor: FAMS.orangeDeep,
          activeColor: FAMS.orangeDeep
        },
        text: { color: FAMS.charcoal, mutedColor: FAMS.steel }
      },
      dark: {
        surface: darkSurfaceScale,
        primary: {
          color: FAMS.orange,
          contrastColor: FAMS.white,
          hoverColor: FAMS.orangeGlow,
          activeColor: FAMS.orangeGlow
        },
        text: { color: FAMS.paper, mutedColor: FAMS.fog }
      }
    }
  }
});

export const primeVueOptions = {
  theme: {
    preset: FamsPreset,
    options: {
      darkModeSelector: '.app-dark',
      // PrimeVue styles sit in a layer BELOW Tailwind utilities, so pt:/class overrides win.
      cssLayer: { name: 'primevue', order: 'theme, base, primevue' }
    }
  }
};
