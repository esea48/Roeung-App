/**
 * NAV_CONFIG factory functions and isActive helper.
 *
 * Two separate configs are needed because the family surfaces include an
 * access token in the URL while the Keeper surface does not.
 */

/**
 * Nav items for the Capture and Book surfaces.
 * Routes are fully-qualified paths using the family access token.
 */
export function createFamilyNavConfig(accessToken, isKeeper = false) {
  const items = [];

  if (isKeeper) {
    items.push({
      id: 'keeper-dashboard',
      route: '/keeper',
      labelEn: 'Keeper Review',
      labelKh: 'ផ្ទាំងគ្រប់គ្រង',
    });
  }

  items.push(
    {
      id: 'book',
      route: `/f/${accessToken}/book`,
      labelEn: 'Family Book',
      labelKh: 'គ្រួសាររបស់យើង',
    },
    {
      id: 'capture',
      route: `/f/${accessToken}/capture`,
      labelEn: 'Record a story',
      labelKh: 'ថតរឿង',
    },
    {
      id: 'chapters',
      // Scrolls to the chapter shelf on Book home — not a distinct route
      route: `/f/${accessToken}/book#chapters`,
      scrollOnly: true,
      labelEn: 'Chapters',
      labelKh: 'ជំពូក',
    },
  );

  return items;
}

/**
 * Nav items for the Keeper surface.
 * stats: { awaiting_review: number, flagged: number }
 * Optionally pass activeStoryFrom ('queue'|'published'|'archive') so the correct
 * nav item is highlighted when viewing a story detail page.
 */
export function createKeeperNavConfig(stats = {}) {
  return [
    {
      id: 'queue',
      route: '/keeper',
      labelEn: 'Review queue',
      labelKh: 'ជួរពិនិត្យ',
      badge: stats.awaiting_review || 0,
      badgeType: 'neutral',
      section: 'review',
    },
    {
      id: 'flagged',
      route: '/keeper?filter=flagged',
      labelEn: 'Flagged',
      labelKh: 'ដែលបានសម្គាល់',
      badge: stats.flagged || 0,
      badgeType: 'warn',
      section: 'review',
    },
    {
      id: 'published',
      route: '/keeper/published',
      labelEn: 'Published',
      labelKh: 'បានបោះពុម្ព',
      section: 'review',
    },
    {
      id: 'archive',
      route: '/keeper/archive',
      labelEn: 'Archive',
      labelKh: 'បណ្ណសារ',
      section: 'review',
    },
    {
      id: 'book',
      route: '/keeper/book',
      labelEn: 'Book',
      labelKh: 'សៀវភៅ',
      section: 'content',
    },
    {
      id: 'members',
      route: '/keeper/members',
      labelEn: 'Family members',
      labelKh: 'សមាជិកគ្រួសារ',
      section: 'content',
    },
    {
      id: 'chapters',
      route: '/keeper/chapters',
      labelEn: 'Chapters',
      labelKh: 'ជំពូក',
      section: 'content',
    },
  ];
}

/**
 * Returns true when an item should be highlighted as active.
 *
 * location: { pathname: string, search: string, state?: { from?: string } }
 * item: one object from createFamilyNavConfig or createKeeperNavConfig
 *
 * Edge cases:
 * - flagged: only active when on /keeper with ?filter=flagged query
 * - queue: active on /keeper root (without flagged filter) AND story detail pages
 *   where location.state.from is 'queue' or absent (default)
 * - published: active on /keeper/published and story detail pages where from='published'
 * - archive: active on /keeper/archive and story detail pages where from='archive'
 * - chapters (family): never active — it's an anchor scroll, not a route
 * - all others: exact match OR path starts with route prefix (ignoring hash/query)
 */
export function isActive(location, item) {
  const { pathname, search, state } = location;

  if (item.id === 'flagged') {
    return pathname === '/keeper' && search === '?filter=flagged';
  }

  const onStoryDetail = pathname.startsWith('/keeper/story/');
  const storyFrom = state?.from;

  if (item.id === 'queue') {
    const onKeeperRoot =
      (pathname === '/keeper' || pathname === '/keeper/') &&
      search !== '?filter=flagged';
    return onKeeperRoot || (onStoryDetail && (!storyFrom || storyFrom === 'queue'));
  }

  if (item.id === 'published') {
    return pathname === '/keeper/published' || (onStoryDetail && storyFrom === 'published');
  }

  if (item.id === 'archive') {
    return pathname === '/keeper/archive' || (onStoryDetail && storyFrom === 'archive');
  }

  // Scroll-only anchors (e.g. family chapters) are never active
  if (item.scrollOnly) return false;

  const routePath = item.route.split('?')[0].split('#')[0];
  if (!routePath || routePath === '/') return false;

  return pathname === routePath || pathname.startsWith(routePath + '/');
}
