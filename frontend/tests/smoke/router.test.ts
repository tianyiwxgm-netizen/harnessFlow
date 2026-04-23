import { describe, it, expect } from 'vitest';
import { routes } from '@/router/index';

describe('router routes (post-WP02 structure)', () => {
  it('has a root route "/" that redirects', () => {
    const root = routes.find((r) => r.path === '/');
    expect(root).toBeDefined();
    expect(root?.redirect).toBeDefined();
  });

  it('has a /tabs parent route with children', () => {
    const tabs = routes.find((r) => r.path === '/tabs');
    expect(tabs).toBeDefined();
    expect(Array.isArray(tabs?.children)).toBe(true);
  });

  it('has the catch-all 404 fallback', () => {
    const fallback = routes.find((r) => r.path === '/:pathMatch(.*)*');
    expect(fallback).toBeDefined();
  });
});
