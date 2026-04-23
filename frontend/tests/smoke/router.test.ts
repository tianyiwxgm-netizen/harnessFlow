import { describe, it, expect } from 'vitest';
import { routes } from '@/router/index';

describe('router routes (WP01 placeholder)', () => {
  it('has a root route "/" named "home"', () => {
    const root = routes.find((r) => r.path === '/');
    expect(root).toBeDefined();
    expect(root?.name).toBe('home');
  });

  it('has 404 fallback', () => {
    const fallback = routes.find((r) => r.path === '/:pathMatch(.*)*');
    expect(fallback).toBeDefined();
  });
});
