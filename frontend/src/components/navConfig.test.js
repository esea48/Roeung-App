import { describe, expect, it } from 'vitest';
import { createFamilyNavConfig, createKeeperNavConfig, isActive } from './navConfig.js';

const TOKEN = 'abc123';
const familyItems = createFamilyNavConfig(TOKEN);
const keeperItems = createKeeperNavConfig({ awaiting_review: 4, flagged: 2 });

function loc(pathname, search = '') {
  return { pathname, search };
}

// Helper: find item by id across either config
function item(id, config = [...familyItems, ...keeperItems]) {
  return config.find((i) => i.id === id);
}

describe('isActive — family surface', () => {
  it('book: active on /f/token/book (exact)', () => {
    expect(isActive(loc(`/f/${TOKEN}/book`), item('book', familyItems))).toBe(true);
  });

  it('book: active on chapter sub-route', () => {
    expect(isActive(loc(`/f/${TOKEN}/book/chapter/1`), item('book', familyItems))).toBe(true);
  });

  it('book: active on story sub-route', () => {
    expect(isActive(loc(`/f/${TOKEN}/book/story/5`), item('book', familyItems))).toBe(true);
  });

  it('capture: active on /f/token/capture', () => {
    expect(isActive(loc(`/f/${TOKEN}/capture`), item('capture', familyItems))).toBe(true);
  });

  it('capture: not active on /f/token/book', () => {
    expect(isActive(loc(`/f/${TOKEN}/book`), item('capture', familyItems))).toBe(false);
  });

  it('chapters (anchor): never active', () => {
    // Anchor-only item has no activatable route
    expect(isActive(loc(`/f/${TOKEN}/book`), item('chapters', familyItems))).toBe(false);
    expect(isActive(loc(`/f/${TOKEN}/book#chapters`), item('chapters', familyItems))).toBe(false);
  });
});

describe('isActive — keeper surface', () => {
  it('queue: active on /keeper (exact)', () => {
    expect(isActive(loc('/keeper'), item('queue', keeperItems))).toBe(true);
  });

  it('queue: active on /keeper/', () => {
    expect(isActive(loc('/keeper/'), item('queue', keeperItems))).toBe(true);
  });

  it('queue: active on /keeper/story/:id', () => {
    expect(isActive(loc('/keeper/story/42'), item('queue', keeperItems))).toBe(true);
  });

  it('queue: NOT active when ?filter=flagged present', () => {
    expect(isActive(loc('/keeper', '?filter=flagged'), item('queue', keeperItems))).toBe(false);
  });

  it('flagged: active on /keeper?filter=flagged', () => {
    expect(isActive(loc('/keeper', '?filter=flagged'), item('flagged', keeperItems))).toBe(true);
  });

  it('flagged: NOT active on /keeper without query', () => {
    expect(isActive(loc('/keeper'), item('flagged', keeperItems))).toBe(false);
  });

  it('members: active on /keeper/members', () => {
    expect(isActive(loc('/keeper/members'), item('members', keeperItems))).toBe(true);
  });

  it('chapters: active on /keeper/chapters', () => {
    expect(isActive(loc('/keeper/chapters'), item('chapters', keeperItems))).toBe(true);
  });

  it('members: NOT active on /keeper/chapters', () => {
    expect(isActive(loc('/keeper/chapters'), item('members', keeperItems))).toBe(false);
  });

  it('book: active on /keeper/book', () => {
    expect(isActive(loc('/keeper/book'), item('book', keeperItems))).toBe(true);
  });
});

describe('createFamilyNavConfig', () => {
  it('routes include accessToken', () => {
    const items = createFamilyNavConfig('mytoken');
    expect(items.find((i) => i.id === 'book').route).toBe('/f/mytoken/book');
    expect(items.find((i) => i.id === 'capture').route).toBe('/f/mytoken/capture');
  });

  it('has bilingual labels', () => {
    familyItems.forEach((i) => {
      expect(i.labelEn).toBeTruthy();
      expect(i.labelKh).toBeTruthy();
    });
  });
});

describe('createKeeperNavConfig', () => {
  it('exposes badge counts from stats', () => {
    const items = createKeeperNavConfig({ awaiting_review: 7, flagged: 3 });
    expect(items.find((i) => i.id === 'queue').badge).toBe(7);
    expect(items.find((i) => i.id === 'flagged').badge).toBe(3);
  });

  it('defaults to 0 badges when stats is empty', () => {
    const items = createKeeperNavConfig();
    expect(items.find((i) => i.id === 'queue').badge).toBe(0);
    expect(items.find((i) => i.id === 'flagged').badge).toBe(0);
  });

  it('sections: queue and flagged are review; members and chapters are content', () => {
    expect(keeperItems.find((i) => i.id === 'queue').section).toBe('review');
    expect(keeperItems.find((i) => i.id === 'flagged').section).toBe('review');
    expect(keeperItems.find((i) => i.id === 'members').section).toBe('content');
    expect(keeperItems.find((i) => i.id === 'chapters').section).toBe('content');
  });
});
