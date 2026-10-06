// fams-ui-standards §1 - the ONLY place hex colours may appear (plus fams-theme.css).
// Source: VINIS x FAMS x MASANA NotebookLM prompt §2 / Mining Operational Intelligence deck.
export const FAMS = {
  charcoal: '#30383D',
  graphite: '#3C4449',
  steel: '#737B80',
  fog: '#D9DADB',
  paper: '#F3F3F1',
  white: '#FFFFFF',
  orange: '#F47A20',
  orangeDeep: '#C95614',
  orangeGlow: '#FF8A2A',
  amber: '#F2A541'
};

// Scales derived from the palette (500 = the document colour).
export const orangeScale = {
  50: '#FEF2E9', 100: '#FDE4D2', 200: '#FBC9A6', 300: '#F9AE79', 400: '#F6934D',
  500: '#F47A20', 600: '#C95614', 700: '#A2440F', 800: '#7A330B', 900: '#532207', 950: '#2B1204'
};
export const deepOrangeScale = {
  50: '#FBEEE7', 100: '#F4D5C4', 200: '#EAB295', 300: '#DE8D63', 400: '#D3703B',
  500: '#C95614', 600: '#A84711', 700: '#86380E', 800: '#652A0A', 900: '#431C07', 950: '#251004'
};
export const amberScale = {
  50: '#FEF6EC', 100: '#FCEBD3', 200: '#F9D6A7', 300: '#F6C17B', 400: '#F4B05E',
  500: '#F2A541', 600: '#D18A2B', 700: '#A86D20', 800: '#7E5118', 900: '#553610', 950: '#2E1D08'
};
export const steelScale = {
  0: '#FFFFFF', 50: '#F3F3F1', 100: '#E6E7E5', 200: '#D9DADB', 300: '#B9BCBE', 400: '#969B9E',
  500: '#737B80', 600: '#5A6267', 700: '#4A5257', 800: '#3C4449', 900: '#30383D', 950: '#22282C'
};
// Dark mode: cards = graphite (surface.900), page = charcoal (surface.950)
export const darkSurfaceScale = {
  0: '#FFFFFF', 50: '#F3F3F1', 100: '#E6E7E5', 200: '#D9DADB', 300: '#B9BCBE', 400: '#969B9E',
  500: '#737B80', 600: '#5A6267', 700: '#4F575C', 800: '#454D52', 900: '#3C4449', 950: '#30383D'
};
