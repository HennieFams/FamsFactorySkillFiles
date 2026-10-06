import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import StatusTag from '@/components/shared/StatusTag.vue';

describe('StatusTag', () => {
  it.each([
    ['critical', 'bg-fams-orange-deep', 'CRITICAL'],
    ['warning', 'bg-fams-amber', 'WARNING'],
    ['active', 'border-fams-orange', 'LIVE'],
    ['healthy', 'border-fams-steel', 'NORMAL'],
    ['offline', 'border-dashed', 'NO DATA']
  ])('%s uses palette colour + label + icon', (status, cls, text) => {
    const w = mount(StatusTag, { props: { status } });
    expect(w.classes()).toContain(cls);
    expect(w.text()).toBe(text);
    expect(w.find('i').exists()).toBe(true);
  });
});
